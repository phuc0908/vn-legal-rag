from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CreatePaymentRequest(BaseModel):
    plan: str  # "plus" | "pro"


class CreatePaymentResponse(BaseModel):
    checkout_url: str
    order_code: int
    amount: int
    plan: str


class TransactionOut(BaseModel):
    id: int
    order_code: str
    plan: str
    amount: int
    status: str
    created_at: datetime
    paid_at: Optional[datetime] = None
