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

    # Security
    SECRET_KEY: str = "Phuc123456789"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # LLM Configuration
    LLM_PROVIDER: str = "groq"
    LLM_MODEL: str = "llama3-8b-8192"
    GEMINI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    LLM_TEMPERATURE: float = 0.5
    LLM_MAX_TOKENS: int = 2048

    # RAG Configuration
    VECTOR_STORE_TYPE: str = "chroma"
    VECTOR_DIMENSION: int = 768
    CHUNK_SIZE: int = 1024
    CHUNK_OVERLAP: int = 256
    SIMILARITY_THRESHOLD: float = 0.3
    TOP_K_RETRIEVAL: int = 5

    # Pinecone (if using)
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_ENVIRONMENT: str = "production"
    PINECONE_INDEX_NAME: str = "legal-docs"

    # Embeddings
    EMBEDDING_MODEL: str = "AITeamVN/Vietnamese_Embedding"

    # Reranker
    RERANKER_ENABLED: bool = True
    RERANKER_MODEL: str = "AITeamVN/Vietnamese_Reranker"
    RERANKER_TOP_K: int = 5
    RETRIEVAL_CANDIDATE_MULTIPLIER: int = 3

    # Hierarchical RAG — Topic Router
    TOPIC_ROUTER_ENABLED: bool = True

    # Hybrid Search — BM25 + Vector
    HYBRID_SEARCH_ENABLED: bool = True
    BM25_INDEX_PATH: str = "./bm25_index.pkl"
    RRF_K: int = 60

    # Retrieval Cache
    RETRIEVAL_CACHE_ENABLED: bool = True
    RETRIEVAL_CACHE_TTL: int = 300  # seconds

    # Database
    DATABASE_URL: Optional[str] = None

    # PayOS Payment Gateway
    PAYOS_CLIENT_ID:     str = ""
    PAYOS_API_KEY:       str = ""
    PAYOS_CHECKSUM_KEY:  str = ""
    PAYOS_RETURN_URL:    str = "http://localhost:5173/payment/result"
    PAYOS_CANCEL_URL:    str = "http://localhost:5173/payment/cancel"

    # CORS — thêm ngrok URL vào đây khi dùng ngrok
    # Ví dụ: ALLOWED_ORIGINS=["https://your-name.ngrok-free.app","http://localhost:3000"]
    ALLOWED_ORIGINS: list = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://127.0.0.1:5173"]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
