from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class ChatTurn(BaseModel):
    """A single message in conversation history"""
    role: str  # "user" or "assistant"
    content: str


class QueryRequest(BaseModel):
    """Request model for RAG query"""
    query: str = Field(..., min_length=1, description="User query")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context")
    top_k: int = Field(5, ge=1, le=20, description="Number of sources to retrieve")
    chu_de_id: Optional[str] = Field(None, description="Filter vectors by topic ID (pdchude.id)")
    chat_history: Optional[List[ChatTurn]] = Field(None, description="Recent conversation turns for context")
    module: Optional[str] = Field(None, description="RAG module: None (full corpus) | 'hon_nhan'")


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

# Auth Schemas
from pydantic import EmailStr

class UserCreate(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    password: str
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserOut(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    
    class Config:
        from_attributes = True

# Conversation Schemas
class MessageOut(BaseModel):
    role: str
    content: str
    created_at: Optional[datetime] = None

class ConversationOut(BaseModel):
    id: str
    user_id: int
    title: Optional[str] = None
    created_at: datetime
    messages: List[MessageOut] = []
