from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class QueryRequest(BaseModel):
    """Request model for RAG query"""
    query: str = Field(..., min_length=1, description="User query")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context")
    top_k: int = Field(5, ge=1, le=20, description="Number of sources to retrieve")


class SourceDocument(BaseModel):
    """Retrieved source document"""
    title: str
    content: str
    relevance_score: float
    metadata: Optional[dict] = None
    url: Optional[str] = None


class QueryResponse(BaseModel):
    """Response model for RAG query"""
    query: str
    answer: str
    sources: List[SourceDocument]
    processing_time: float
    model_used: Optional[str] = None


class Message(BaseModel):
    """Chat message"""
    role: str = Field(..., description="'user' or 'assistant'")
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    sources: Optional[List[SourceDocument]] = None


class ConversationRequest(BaseModel):
    """Conversation request"""
    message: str
    conversation_id: Optional[str] = None


class ConversationResponse(BaseModel):
    """Conversation response"""
    conversation_id: str
    messages: List[Message]
    answer: str
    sources: List[SourceDocument]


class DocumentUpload(BaseModel):
    """Document upload request"""
    content: str
    metadata: dict = Field(default_factory=dict)
    title: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    llm_configured: bool
    vector_store_ready: bool
