"""
User model for TikTok Shop Creator CRM
Handles all user-related data including profile information, social media handles,
and role-specific fields for creators, agencies, and brands.
"""

from datetime import datetime, date
from typing import Optional, List
from uuid import UUID, uuid4
from enum import Enum as PyEnum

from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, Integer, 
    Numeric, Text, JSON, Enum, ForeignKey, Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql import func

from app.db.base_class import Base


class UserRole(str, PyEnum):
    """User role enumeration"""
    AGENCY = "agency"
    CREATOR = "creator"
    BRAND = "brand"
    ADMIN = "admin"


class GenderType(str, PyEnum):
    """Gender type enumeration"""
    MALE = "male"
    FEMALE = "female"
    NON_BINARY = "non_binary"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class User(Base):
    """
    Main user model containing all profile information.
    Supports multiple roles: creator, agency, brand, and admin.
    """
    __tablename__ = "users"
    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_username", "username"),
        Index("idx_users_role", "role"),
        Index("idx_users_created_at", "created_at"),
        Index("idx_users_current_gmv", "current_gmv"),  # New index for badge queries
        CheckConstraint("engagement_rate >= 0 AND engagement_rate <= 100", name="check_engagement_rate"),
        CheckConstraint("profile_completion_percentage >= 0 AND profile_completion_percentage <= 100", 
                       name="check_profile_completion"),
        CheckConstraint("current_gmv >= 0", name="check_current_gmv"),  # New constraint
        {"schema": "users", "extend_existing": True}
    )

    # Primary Key
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)

    # Authentication fields
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    
    # Role and status
    role = Column(Enum(UserRole, name="user_role", schema="users"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    
    # Contact information
    phone = Column(String(20))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login = Column(DateTime(timezone=True))

    # Profile information
    first_name = Column(String(100))
    last_name = Column(String(100))
    date_of_birth = Column(Date)
    gender = Column(Enum(GenderType, name="gender_type", schema="users"))
    profile_image_url = Column(Text)
    bio = Column(Text)
    
    # Address information for shipping
    address_line1 = Column(String(255))
    address_line2 = Column(String(255))
    city = Column(String(100))
    state = Column(String(100))
    postal_code = Column(String(20))
    country = Column(String(100), default='US')
    
    # Social media handles
    tiktok_handle = Column(String(100))
    tiktok_user_id = Column(String(100))
    discord_handle = Column(String(100))
    discord_user_id = Column(String(100))
    instagram_handle = Column(String(100))
    
    # Creator specific fields
    content_niche = Column(String(100))
    follower_count = Column(Integer, default=0)
    average_views = Column(Integer, default=0)
    engagement_rate = Column(Numeric(5, 2), default=0.00)
    current_gmv = Column(Numeric(12, 2), default=0.00)  # NEW FIELD for badge system
    
    # Agency/Brand specific fields
    company_name = Column(String(200))
    website_url = Column(Text)
    tax_id = Column(String(50))
    
    # Profile completion tracking
    profile_completion_percentage = Column(Integer, default=0)
    
    # Preferences
    notification_preferences = Column(JSON, default=dict)
    timezone = Column(String(50), default='UTC')
    
    # Relationships
    tokens = relationship("UserToken", back_populates="user", cascade="all, delete-orphan")
    badges = relationship("CreatorBadge", back_populates="creator", cascade="all, delete-orphan")
    audience_demographics = relationship("CreatorAudienceDemographic", back_populates="creator", cascade="all, delete-orphan")
    
    # Computed properties
    @hybrid_property
    def full_name(self) -> Optional[str]:
        """Get full name from first and last name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name or None
    
    @hybrid_property
    def has_complete_address(self) -> bool:
        """Check if user has complete address"""
        return all([
            self.address_line1,
            self.city,
            self.state,
            self.postal_code,
            self.country
        ])
    
    @hybrid_property
    def has_social_media_connected(self) -> bool:
        """Check if user has connected any social media"""
        return any([
            self.tiktok_handle,
            self.discord_handle,
            self.instagram_handle
        ])
    
    @hybrid_property
    def is_creator(self) -> bool:
        """Check if user is a creator"""
        return self.role == UserRole.CREATOR
    
    @hybrid_property
    def is_agency(self) -> bool:
        """Check if user is an agency"""
        return self.role == UserRole.AGENCY
    
    @hybrid_property
    def is_brand(self) -> bool:
        """Check if user is a brand"""
        return self.role == UserRole.BRAND
    
    @hybrid_property
    def is_admin(self) -> bool:
        """Check if user is an admin"""
        return self.role == UserRole.ADMIN
    
    # Validators
    @validates("email")
    def validate_email(self, key, email):
        """Validate email format"""
        if email:
            return email.lower()
        return email
    
    @validates("username")
    def validate_username(self, key, username):
        """Validate username format"""
        if username:
            return username.lower()
        return username
    
    @validates("engagement_rate")
    def validate_engagement_rate(self, key, rate):
        """Validate engagement rate is within bounds"""
        if rate is not None:
            if rate < 0 or rate > 100:
                raise ValueError("Engagement rate must be between 0 and 100")
        return rate
    
    @validates("current_gmv")
    def validate_current_gmv(self, key, gmv):
        """Validate GMV is non-negative"""
        if gmv is not None and gmv < 0:
            raise ValueError("Current GMV cannot be negative")
        return gmv
    
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"


class UserToken(Base):
    """
    User authentication tokens for password reset, email verification, etc.
    """
    __tablename__ = "user_tokens"
    __table_args__ = (
        Index("idx_user_tokens_user_id", "user_id"),
        Index("idx_user_tokens_token_type", "token_type"),
        Index("idx_user_tokens_expires_at", "expires_at"),
        {"schema": "users"}
    )
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.users.id", ondelete="CASCADE"), nullable=False)
    token_type = Column(String(50), nullable=False)  # 'oauth', 'reset_password', 'email_verification'
    token_value = Column(String(500), nullable=False)
    expires_at = Column(DateTime(timezone=True))
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="tokens")
    
    def __repr__(self):
        return f"<UserToken(id={self.id}, user_id={self.user_id}, type={self.token_type})>"