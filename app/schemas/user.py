from pydantic import BaseModel, EmailStr, validator, Field, constr
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID
import re

class UserBase(BaseModel):
    email: EmailStr
    role: str
    first_name: Optional[constr(min_length=1, max_length=100)] = None
    last_name: Optional[constr(min_length=1, max_length=100)] = None
    phone: Optional[str] = None
    tiktok_handle: Optional[str] = None
    
    @validator('phone')
    def validate_phone(cls, v):
        if v:
            phone_regex = re.compile(r'^\+?1?\d{9,15}$')
            if not phone_regex.match(v):
                raise ValueError('Invalid phone number format')
        return v
    
    @validator('tiktok_handle')
    def validate_tiktok_handle(cls, v):
        if v:
            if not v.startswith('@'):
                v = f"@{v}"
            if not re.match(r'^@[a-zA-Z0-9_.]+$', v):
                raise ValueError('Invalid TikTok handle format')
        return v

class UserCreate(UserBase):
    password: constr(min_length=8)
    
    @validator('password')
    def validate_password(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        return v

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    bio: Optional[str] = None
    phone: Optional[str] = None
    tiktok_handle: Optional[str] = None
    avatar_url: Optional[str] = None

class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    role: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    tiktok_handle: Optional[str] = None
    discord_user_id: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool
    is_verified: bool
    is_profile_complete: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class LoginRequest(BaseModel):
    email: EmailStr
    password: str