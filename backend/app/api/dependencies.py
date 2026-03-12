from typing import Optional
from app.core.config import settings
from app.rag.pipeline import get_rag_pipeline


async def get_rag_pipeline():
    """Dependency: Get RAG pipeline"""
    return get_rag_pipeline()
