import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API Configuration
    API_TITLE: str = "Vietnamese Legal RAG API"
    API_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # LLM Configuration
    LLM_PROVIDER: str = "gemini"
    LLM_MODEL: str = "gemini-3-flash-preview"
    GEMINI_API_KEY: Optional[str] = None
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 2048

    # RAG Configuration
    VECTOR_STORE_TYPE: str = "chroma"
    VECTOR_DIMENSION: int = 768
    CHUNK_SIZE: int = 1024
    CHUNK_OVERLAP: int = 256
    SIMILARITY_THRESHOLD: float = 0.5
    TOP_K_RETRIEVAL: int = 5

    # Pinecone (if using)
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_ENVIRONMENT: str = "production"
    PINECONE_INDEX_NAME: str = "legal-docs"

    # Embeddings
    EMBEDDING_MODEL: str = "hiieu/halong_embedding"

    # Database
    DATABASE_URL: Optional[str] = None

    # CORS
    ALLOWED_ORIGINS: list = ["http://localhost:3000", "http://127.0.0.1:3000"]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
