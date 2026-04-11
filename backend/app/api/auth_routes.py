from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.core.auth import verify_password, create_access_token, get_password_hash, get_current_user
from app.models.schemas import UserCreate, Token, UserOut
from app.db.database import query_one, get_db
import pymysql

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
    
    access_token = create_access_token(data={"sub": user["username"]})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserOut)
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return current_user
