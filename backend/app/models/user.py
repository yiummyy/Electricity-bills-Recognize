from typing import Optional
from pydantic import BaseModel, Field
import datetime


class UserCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=32)
    password: str = Field(..., min_length=6, max_length=128)


class UserAdminCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=32)
    password: str = Field(..., min_length=6, max_length=128)
    role: str = Field(default="user", pattern="^(admin|user)$")


class UserAdminUpdate(BaseModel):
    password: Optional[str] = Field(default=None, min_length=6, max_length=128)
    role: Optional[str] = Field(default=None, pattern="^(admin|user)$")


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    username: str
    role: str
    created_at: datetime.datetime


class UserListItem(BaseModel):
    username: str
    role: str
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str
