from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from app.core.config import settings
from app.api.routes import router as api_router
from app.api.law_routes import router as law_router
from app.api.auth_routes import router as auth_router
from app.api.conversation_routes import router as conv_router
from app.api.bookmark_routes import router as bookmark_router
from app.api.history_routes import router as history_router
from app.api.admin_routes import router as admin_router
from app.db.database import get_db
from app.rag.pipeline import get_rag_pipeline
import uvicorn
import os

def _run_migration(cur, sql):
    try:
        cur.execute(sql)
    except Exception:
        pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    with get_db() as conn:
        with conn.cursor() as cur:
            _run_migration(cur, "ALTER TABLE users ADD COLUMN avatar_url MEDIUMTEXT NULL")
            _run_migration(cur, "ALTER TABLE users MODIFY COLUMN avatar_url MEDIUMTEXT NULL")
            _run_migration(cur, "ALTER TABLE users ADD COLUMN is_admin TINYINT(1) NOT NULL DEFAULT 0")
            _run_migration(cur, "ALTER TABLE users ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP")
            _run_migration(cur, "ALTER TABLE conversations ADD COLUMN is_deleted TINYINT(1) NOT NULL DEFAULT 0")
            _run_migration(cur, "ALTER TABLE messages ADD COLUMN is_deleted TINYINT(1) NOT NULL DEFAULT 0")
            conn.commit()
    print("[STARTUP] Pre-loading RAG pipeline (embedding model + reranker + BM25)...")
    get_rag_pipeline()
    print("[STARTUP] Sẵn sàng nhận request.")
    yield


# Create FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api")
app.include_router(law_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(conv_router, prefix="/api")
app.include_router(bookmark_router, prefix="/api")
app.include_router(history_router, prefix="/api")
app.include_router(admin_router, prefix="/api")

# Serve frontend static file
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.exists(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/", include_in_schema=False)
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str = ""):
        # Không override các route /api và /docs
        index = os.path.join(FRONTEND_DIST, "index.html")
        return FileResponse(index)
else:
    @app.get("/")
    async def root():
        return {"title": settings.API_TITLE, "version": settings.API_VERSION, "status": "running"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )
