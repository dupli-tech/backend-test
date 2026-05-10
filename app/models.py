import re

from pydantic import BaseModel, field_validator

_DOCUMENT_RE = re.compile(r"^\d{11}$|^\d{14}$")


class CustomerCreate(BaseModel):
    name: str
    email: str
    document: str  # CPF (11 dígitos) ou CNPJ (14 dígitos)

    @field_validator("document")
    @classmethod
    def validate_document(cls, v: str) -> str:
        if not _DOCUMENT_RE.match(v):
            raise ValueError(
                "document must be 11 digits (CPF) or 14 digits (CNPJ)"
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
