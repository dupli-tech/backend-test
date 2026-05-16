import re
from typing import Generic, TypeVar

from pydantic import BaseModel, field_validator

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    offset: int
    limit: int

_DOCUMENT_RE = re.compile(r"^\d{11}$|^\d{14}$")
_PHONE_BR_RE = re.compile(r"^\+55\d{2}9\d{8}$")


class CustomerCreate(BaseModel):
    name: str
    email: str
    document: str  # CPF (11 dígitos) ou CNPJ (14 dígitos)
    phone: str
    password: str

    @field_validator("document")
    @classmethod
    def validate_document(cls, v: str) -> str:
        if not _DOCUMENT_RE.match(v):
            raise ValueError(
                "document must be 11 digits (CPF) or 14 digits (CNPJ)"
            )
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not _PHONE_BR_RE.match(v):
            raise ValueError(
                "phone must be Brazilian E.164 format: +55 + DDD + 9 + 8 digits"
            )
        return v


class CustomerUpdate(BaseModel):
    name: str | None = None
    email: str | None = None


class Customer(BaseModel):
    id: str
    name: str
    email: str
    document: str
    phone: str
    is_active: bool = True
    balance: float = 0.0


class CustomerStored(BaseModel):
    id: str
    name: str
    email: str
    document: str
    phone: str
    hashed_password: str
    is_active: bool = True
    balance: float = 0.0
