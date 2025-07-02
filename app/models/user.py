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
        CheckConstraint("engagement_rate >= 0 AND engagement_rate <= 100", name="check_engagement_rate"),
        CheckConstraint("profile_completion_percentage >= 0 AND profile_completion_percentage <= 100", 
                       name="check_profile_completion"),
        {"schema": "users"}
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
    country = Column(String(100), default="US")

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

    # Agency/Brand specific fields
    company_name = Column(String(200))
    website_url = Column(Text)
    tax_id = Column(String(50))

    # Profile completion tracking
    profile_completion_percentage = Column(Integer, default=0)

    # Preferences
    notification_preferences = Column(JSON, default=dict)
    timezone = Column(String(50), default="UTC")

    # Relationships
    tokens = relationship("UserToken", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
    badges = relationship("CreatorBadge", back_populates="creator", cascade="all, delete-orphan", lazy="dynamic")
    audience_demographics = relationship("CreatorAudienceDemographic", back_populates="creator", 
                                       cascade="all, delete-orphan", lazy="dynamic")

    @validates("email")
    def validate_email(self, key: str, email: str) -> str:
        """Validate email format"""
        if not email or "@" not in email:
            raise ValueError("Invalid email address")
        return email.lower().strip()

    @validates("username")
    def validate_username(self, key: str, username: str) -> str:
        """Validate username format"""
        if not username or len(username) < 3:
            raise ValueError("Username must be at least 3 characters long")
        return username.lower().strip()

    @validates("phone")
    def validate_phone(self, key: str, phone: Optional[str]) -> Optional[str]:
        """Validate and format phone number"""
        if phone:
            # Remove common formatting characters
            cleaned = "".join(filter(str.isdigit, phone))
            if len(cleaned) < 10:
                raise ValueError("Invalid phone number")
            return cleaned
        return phone

    @validates("engagement_rate")
    def validate_engagement_rate(self, key: str, rate: Optional[float]) -> Optional[float]:
        """Validate engagement rate is within bounds"""
        if rate is not None and (rate < 0 or rate > 100):
            raise ValueError("Engagement rate must be between 0 and 100")
        return rate

    @validates("profile_completion_percentage")
    def validate_completion_percentage(self, key: str, percentage: int) -> int:
        """Validate profile completion percentage"""
        if percentage < 0 or percentage > 100:
            raise ValueError("Profile completion percentage must be between 0 and 100")
        return percentage

    @hybrid_property
    def full_name(self) -> Optional[str]:
        """Get user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        return None

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

    @hybrid_property
    def has_complete_address(self) -> bool:
        """Check if user has complete shipping address"""
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

    def calculate_profile_completion(self) -> int:
        """
        Calculate profile completion percentage based on role.
        Returns a value between 0 and 100.
        """
        required_fields = {
            # Common fields for all roles (40%)
            "basic": [
                self.email,
                self.username,
                self.first_name,
                self.last_name,
                self.phone
            ],
            # Personal info (20%)
            "personal": [
                self.date_of_birth,
                self.gender,
                self.profile_image_url,
                self.bio
            ],
            # Address info (20%)
            "address": [
                self.address_line1,
                self.city,
                self.state,
                self.postal_code
            ]
        }

        # Role-specific fields (20%)
        if self.role == UserRole.CREATOR:
            required_fields["role_specific"] = [
                self.tiktok_handle,
                self.content_niche,
                bool(self.follower_count),
                bool(self.average_views)
            ]
        elif self.role in [UserRole.AGENCY, UserRole.BRAND]:
            required_fields["role_specific"] = [
                self.company_name,
                self.website_url,
                self.tax_id
            ]
        else:  # Admin
            required_fields["role_specific"] = []

        # Calculate weights
        weights = {
            "basic": 40,
            "personal": 20,
            "address": 20,
            "role_specific": 20
        }

        total_percentage = 0
        for section, fields in required_fields.items():
            if fields:
                completed = sum(1 for field in fields if field)
                section_percentage = (completed / len(fields)) * weights[section]
                total_percentage += section_percentage

        return int(total_percentage)

    def update_profile_completion(self) -> None:
        """Update the profile completion percentage"""
        self.profile_completion_percentage = self.calculate_profile_completion()

    def __repr__(self) -> str:
        """String representation of user"""
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"


class UserToken(Base):
    """
    User authentication tokens for various purposes
    (OAuth, password reset, email verification, etc.)
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
    token_value = Column(String(500), nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True))
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="tokens")

    @hybrid_property
    def is_expired(self) -> bool:
        """Check if token is expired"""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False

    @hybrid_property
    def is_valid(self) -> bool:
        """Check if token is valid (not used and not expired)"""
        return not self.is_used and not self.is_expired

    def __repr__(self) -> str:
        """String representation of token"""
        return f"<UserToken(id={self.id}, type={self.token_type}, user_id={self.user_id})>"