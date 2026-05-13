from enum import StrEnum

from pydantic import BaseModel


class TransactionStatus(StrEnum):
    completed = "completed"


class TransactionCreate(BaseModel):
    from_customer_id: str
    to_customer_id: str
    amount: float


class DepositRequest(BaseModel):
    amount: float


class Transaction(BaseModel):
    id: str
    from_customer_id: str
    to_customer_id: str
    amount: float
    created_at: str
    status: TransactionStatus
