from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
import enum

class UserRole(enum.Enum):
    ADMIN = "admin"
    USER = "user"

class RegisterRequest(BaseModel):
    username: Optional[str]
    email: EmailStr
    password: str
    role: UserRole
    contact_number: Optional[str]

class RegisterData(BaseModel):
    id: int
    username: Optional[str]
    email: EmailStr
    role: str

class RegisterResponse(BaseModel):
    status: str
    data: RegisterData



class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    session_id: str


class RefreshRequest(BaseModel):
    refresh_token: str
    session_id: str


class LogoutRequest(BaseModel):
    session_id: str