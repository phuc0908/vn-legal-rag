from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import router as api_router
from app.api.law_routes import router as law_router
from app.api.auth_routes import router as auth_router
from app.api.conversation_routes import router as conv_router
import uvicorn


# Create FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    debug=settings.DEBUG,
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


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "title": settings.API_TITLE,
        "version": settings.API_VERSION,
        "status": "running"
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )
