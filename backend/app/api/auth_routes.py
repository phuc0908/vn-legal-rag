from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
from app.core.auth import verify_password, create_access_token, get_password_hash, get_current_user
from app.models.schemas import UserCreate, Token, UserOut, UserUpdate, PasswordChange
from app.db.database import query_one, get_db
import pymysql
import base64

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5 MB

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserOut)
async def register(user_in: UserCreate):
    # Check username uniqueness
    existing_user = query_one("SELECT id FROM users WHERE username = %s", (user_in.username,))
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    # Check email uniqueness only if provided (NULL = NULL is FALSE in SQL)
    if user_in.email:
        existing_email = query_one("SELECT id FROM users WHERE email = %s", (user_in.email,))
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_pwd = get_password_hash(user_in.password)
    
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (username, email, hashed_password, full_name) VALUES (%s, %s, %s, %s)",
                (user_in.username, user_in.email, hashed_pwd, user_in.full_name)
            )
            user_id = cur.lastrowid
            conn.commit()
            
    return {"id": user_id, "username": user_in.username, "email": user_in.email, "full_name": user_in.full_name}

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = query_one("SELECT * FROM users WHERE username = %s", (form_data.username,))
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đã bị vô hiệu hóa. Vui lòng liên hệ quản trị viên.",
        )
    
    access_token = create_access_token(data={"sub": user["username"]})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserOut)
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return current_user

@router.put("/me", response_model=UserOut)
async def update_profile(data: UserUpdate, current_user: dict = Depends(get_current_user)):
    if data.email:
        existing = query_one(
            "SELECT id FROM users WHERE email = %s AND id != %s",
            (data.email, current_user["id"])
        )
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use")

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET email = COALESCE(%s, email), full_name = COALESCE(%s, full_name) WHERE id = %s",
                (data.email, data.full_name, current_user["id"])
            )
            conn.commit()

    updated = query_one("SELECT id, username, email, full_name, avatar_url FROM users WHERE id = %s", (current_user["id"],))
    return updated

@router.post("/me/avatar", response_model=UserOut)
async def upload_avatar(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận ảnh JPG, PNG, WebP hoặc GIF.")

    contents = await file.read()
    if len(contents) > MAX_AVATAR_SIZE:
        raise HTTPException(status_code=400, detail="Ảnh không được vượt quá 5MB.")

    data_uri = f"data:{file.content_type};base64,{base64.b64encode(contents).decode()}"

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET avatar_url = %s WHERE id = %s", (data_uri, current_user["id"]))
            conn.commit()

    updated = query_one("SELECT id, username, email, full_name, avatar_url FROM users WHERE id = %s", (current_user["id"],))
    return updated


@router.put("/me/password")
async def change_password(data: PasswordChange, current_user: dict = Depends(get_current_user)):
    user = query_one("SELECT hashed_password FROM users WHERE id = %s", (current_user["id"],))
    if not verify_password(data.current_password, user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Mật khẩu hiện tại không đúng")

    new_hash = get_password_hash(data.new_password)
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET hashed_password = %s WHERE id = %s", (new_hash, current_user["id"]))
            conn.commit()

    return {"message": "Đổi mật khẩu thành công"}
