from enum import StrEnum
from typing import Literal

from pydantic import BaseModel


class UserRole(StrEnum):
    admin = "admin"
    operator = "operator"


class LoginRequest(BaseModel):
    email: str
    password: str
    entity_type: Literal["user", "customer"]


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
