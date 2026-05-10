from pydantic import BaseModel


class CustomerCreate(BaseModel):
    name: str
    email: str
    document: str  # CPF ou CNPJ


class CustomerUpdate(BaseModel):
    name: str | None = None
    email: str | None = None


class Customer(BaseModel):
    id: str
    name: str
    email: str
    document: str
