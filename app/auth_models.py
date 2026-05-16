from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, model_validator


class UserRole(StrEnum):
    admin = "admin"
    operator = "operator"


class LoginRequest(BaseModel):
    email: str | None = None
    phone: str | None = None
    password: str
    entity_type: Literal["user", "customer"]

    @model_validator(mode="after")
    def check_email_or_phone(self) -> Self:
        if self.email and self.phone:
            raise ValueError("Provide either email or phone, not both")
        if not self.email and not self.phone:
            raise ValueError("Either email or phone is required")
        return self


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: UserRole = UserRole.operator


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: UserRole


class UserStored(BaseModel):
    id: str
    name: str
    email: str
    hashed_password: str
    role: UserRole
