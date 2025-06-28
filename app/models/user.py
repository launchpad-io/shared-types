from sqlalchemy import Column, String, Enum, DateTime, Boolean, Index, Text, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
import enum
from typing import Optional

class UserRole(str, enum.Enum):
    AGENCY = "agency"
    CREATOR = "creator" 
    BRAND = "brand"
    ADMIN = "admin"

class PlatformUser(Base):
    __tablename__ = "platform_users"  # Changed from "users"
    
    # Core fields
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20), unique=True, nullable=True, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False, index=True)
    
    # Profile fields
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    bio = Column(Text, nullable=True)
    avatar_url = Column(String(500), nullable=True)
    
    # Platform specific
    tiktok_handle = Column(String(100), unique=True, nullable=True, index=True)
    discord_user_id = Column(String(100), unique=True, nullable=True, index=True)
    
    # Status fields
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_profile_complete = Column(Boolean, default=False, nullable=False, index=True)
    
    # Security
    last_login_at = Column(DateTime, nullable=True)
    last_login_ip = Column(String(45), nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    
    # Metadata
    settings = Column(JSON, default=dict)
    metadata = Column(JSON, default=dict)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_platform_users_email_active', 'email', 'is_active'),
        Index('idx_platform_users_role_active', 'role', 'is_active'),
        Index('idx_platform_users_created_at', 'created_at'),
    )