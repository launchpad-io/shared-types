"""
User schemas for TikTok Shop Creator CRM
Handles all user-related data validation and serialization including
profile updates, authentication, and role-specific fields.
"""

from datetime import datetime, date
from typing import Optional, Dict, List, Any, Annotated
from uuid import UUID
from enum import Enum
import re

from pydantic import (
    BaseModel, Field, EmailStr, field_validator, 
    model_validator, ConfigDict, StringConstraints
)

from app.models.user import UserRole, GenderType


# Type aliases for validation
PhoneNumber = Annotated[str, StringConstraints(pattern=r'^\+?1?\d{9,15}$', strip_whitespace=True)]
Username = Annotated[str, StringConstraints(pattern=r'^[a-zA-Z0-9_-]{3,50}$', to_lower=True, strip_whitespace=True)]
PostalCode = Annotated[str, StringConstraints(pattern=r'^[A-Z0-9\s-]{3,10}$', to_upper=True, strip_whitespace=True)]
TaxId = Annotated[str, StringConstraints(pattern=r'^[A-Z0-9-]{5,20}$', to_upper=True, strip_whitespace=True)]
SocialHandle = Annotated[str, StringConstraints(pattern=r'^[a-zA-Z0-9_.]{3,30}$', strip_whitespace=True)]


class UserBase(BaseModel):
    """Base user schema with common fields"""
    email: Optional[EmailStr] = None
    username: Optional[Username] = None
    role: Optional[UserRole] = None
    first_name: Optional[Annotated[str, StringConstraints(min_length=1, max_length=100)]] = None
    last_name: Optional[Annotated[str, StringConstraints(min_length=1, max_length=100)]] = None
    phone: Optional[PhoneNumber] = None

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class UserCreate(BaseModel):
    """Schema for user creation (used by auth service)"""
    email: EmailStr
    username: Username
    password: Annotated[str, StringConstraints(min_length=8, max_length=100)]
    role: UserRole
    first_name: Optional[Annotated[str, StringConstraints(min_length=1, max_length=100)]] = None
    last_name: Optional[Annotated[str, StringConstraints(min_length=1, max_length=100)]] = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Ensure password meets security requirements"""
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")
        return v


class PersonalInfoUpdate(BaseModel):
    """Schema for updating personal information"""
    phone: Optional[PhoneNumber] = None
    date_of_birth: Optional[date] = None
    gender: Optional[GenderType] = None
    profile_image_url: Optional[str] = None
    bio: Optional[Annotated[str, StringConstraints(max_length=500)]] = None

    @field_validator("date_of_birth")
    @classmethod
    def validate_age(cls, v: Optional[date]) -> Optional[date]:
        """Ensure user is at least 13 years old"""
        if v:
            today = date.today()
            age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
            if age < 13:
                raise ValueError("User must be at least 13 years old")
            if age > 120:
                raise ValueError("Invalid date of birth")
        return v

    @field_validator("profile_image_url", mode='before')
    @classmethod
    def validate_image_url(cls, v: Optional[str]) -> Optional[str]:
        """Ensure image URL is from allowed domains"""
        if v:
            allowed_domains = [
                "cloudinary.com",
                "s3.amazonaws.com",
                "storage.googleapis.com",
                "res.cloudinary.com"
            ]
            if not any(domain in v for domain in allowed_domains):
                raise ValueError("Profile image must be hosted on approved CDN")
        return v

    model_config = ConfigDict(use_enum_values=True, json_encoders={date: lambda v: v.isoformat()})


class AddressUpdate(BaseModel):
    """Schema for updating address information"""
    address_line1: Optional[Annotated[str, StringConstraints(min_length=5, max_length=255)]] = None
    address_line2: Optional[Annotated[str, StringConstraints(max_length=255)]] = None
    city: Optional[Annotated[str, StringConstraints(min_length=2, max_length=100)]] = None
    state: Optional[Annotated[str, StringConstraints(min_length=2, max_length=100)]] = None
    postal_code: Optional[PostalCode] = None
    country: Optional[Annotated[str, StringConstraints(min_length=2, max_length=100)]] = Field(None, description="ISO country code")

    @field_validator("country")
    @classmethod
    def validate_country(cls, v: Optional[str]) -> Optional[str]:
        """Validate country code"""
        if v:
            # List of supported countries (can be extended)
            supported_countries = ["US", "CA", "GB", "AU", "NZ", "MX"]
            v = v.upper()
            if v not in supported_countries:
                raise ValueError(f"Country must be one of: {', '.join(supported_countries)}")
        return v

    @model_validator(mode='after')
    def validate_complete_address(self) -> 'AddressUpdate':
        """Ensure address is complete if any field is provided"""
        address_fields = ["address_line1", "city", "state", "postal_code"]
        provided_fields = [f for f in address_fields if getattr(self, f, None)]
        
        if provided_fields and len(provided_fields) < len(address_fields):
            missing = set(address_fields) - set(provided_fields)
            raise ValueError(f"Incomplete address. Missing fields: {', '.join(missing)}")
        
        return self


class SocialMediaUpdate(BaseModel):
    """Schema for updating social media handles"""
    tiktok_handle: Optional[SocialHandle] = None
    discord_handle: Optional[Annotated[str, StringConstraints(pattern=r'^.{2,32}#[0-9]{4}$|^[a-zA-Z0-9_.]{2,32}$')]] = None
    instagram_handle: Optional[SocialHandle] = None

    @field_validator("tiktok_handle", "instagram_handle")
    @classmethod
    def validate_social_handle(cls, v: Optional[str]) -> Optional[str]:
        """Remove @ symbol if present"""
        if v and v.startswith("@"):
            return v[1:]
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tiktok_handle": "creator123",
                "discord_handle": "creator#1234",
                "instagram_handle": "creator_insta"
            }
        }
    )


class CreatorDetailsUpdate(BaseModel):
    """Schema for updating creator-specific details"""
    content_niche: Optional[Annotated[str, StringConstraints(min_length=3, max_length=100)]] = None
    follower_count: Optional[Annotated[int, Field(ge=0, le=1000000000)]] = None
    average_views: Optional[Annotated[int, Field(ge=0, le=1000000000)]] = None
    engagement_rate: Optional[float] = Field(None, ge=0, le=100)

    @field_validator("content_niche")
    @classmethod
    def validate_niche(cls, v: Optional[str]) -> Optional[str]:
        """Validate content niche from allowed list"""
        if v:
            allowed_niches = [
                "fashion", "beauty", "lifestyle", "fitness", "food",
                "travel", "tech", "gaming", "education", "entertainment",
                "home", "pets", "parenting", "business", "other"
            ]
            v_lower = v.lower()
            if v_lower not in allowed_niches:
                raise ValueError(f"Content niche must be one of: {', '.join(allowed_niches)}")
            return v_lower
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "content_niche": "fashion",
                "follower_count": 50000,
                "average_views": 10000,
                "engagement_rate": 5.5
            }
        }
    )


class CompanyDetailsUpdate(BaseModel):
    """Schema for updating agency/brand company details"""
    company_name: Optional[Annotated[str, StringConstraints(min_length=2, max_length=200)]] = None
    website_url: Optional[str] = None
    tax_id: Optional[TaxId] = None

    @field_validator("website_url", mode='before')
    @classmethod
    def validate_website(cls, v: Optional[str]) -> Optional[str]:
        """Ensure website URL includes protocol"""
        if v and not v.startswith(("http://", "https://")):
            return f"https://{v}"
        return v


class NotificationPreferences(BaseModel):
    """Schema for notification preferences"""
    email_notifications: bool = True
    sms_notifications: bool = True
    push_notifications: bool = False
    campaign_updates: bool = True
    payment_alerts: bool = True
    weekly_digest: bool = True
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email_notifications": True,
                "sms_notifications": True,
                "push_notifications": False,
                "campaign_updates": True,
                "payment_alerts": True,
                "weekly_digest": True
            }
        }
    )


class UserProfileUpdate(BaseModel):
    """Combined schema for bulk profile updates"""
    # Personal info
    first_name: Optional[Annotated[str, StringConstraints(min_length=1, max_length=100)]] = None
    last_name: Optional[Annotated[str, StringConstraints(min_length=1, max_length=100)]] = None
    phone: Optional[PhoneNumber] = None
    date_of_birth: Optional[date] = None
    gender: Optional[GenderType] = None
    profile_image_url: Optional[str] = None
    bio: Optional[Annotated[str, StringConstraints(max_length=500)]] = None
    
    # Address
    address_line1: Optional[Annotated[str, StringConstraints(min_length=5, max_length=255)]] = None
    address_line2: Optional[Annotated[str, StringConstraints(max_length=255)]] = None
    city: Optional[Annotated[str, StringConstraints(min_length=2, max_length=100)]] = None
    state: Optional[Annotated[str, StringConstraints(min_length=2, max_length=100)]] = None
    postal_code: Optional[PostalCode] = None
    country: Optional[Annotated[str, StringConstraints(min_length=2, max_length=100)]] = None
    
    # Social media
    tiktok_handle: Optional[SocialHandle] = None
    discord_handle: Optional[str] = None
    instagram_handle: Optional[SocialHandle] = None
    
    # Preferences
    timezone: Optional[str] = Field(None, description="IANA timezone string")
    notification_preferences: Optional[NotificationPreferences] = None

    model_config = ConfigDict(
        use_enum_values=True,
        from_attributes=True
    )


class ProfileCompletionItem(BaseModel):
    """Schema for individual profile completion items"""
    name: str
    completed: bool
    description: str
    category: str = Field(..., description="Category: basic, personal, address, social, role_specific")


class ProfileCompletionStatus(BaseModel):
    """Schema for profile completion status response"""
    completion_percentage: int = Field(..., ge=0, le=100)
    total_fields: int
    completed_fields: int
    missing_fields: List[str]
    completion_items: List[ProfileCompletionItem]
    next_steps: List[str] = Field(..., description="Suggested next actions")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "completion_percentage": 75,
                "total_fields": 20,
                "completed_fields": 15,
                "missing_fields": ["phone", "address_line1", "city", "state", "postal_code"],
                "completion_items": [
                    {
                        "name": "Basic Information",
                        "completed": True,
                        "description": "Email, username, and name",
                        "category": "basic"
                    }
                ],
                "next_steps": ["Complete your shipping address", "Add your phone number"]
            }
        }
    )


class UserResponse(BaseModel):
    """Schema for user response"""
    id: UUID
    email: EmailStr
    username: str
    role: UserRole
    is_active: bool
    email_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime]
    
    # Profile info
    first_name: Optional[str]
    last_name: Optional[str]
    full_name: Optional[str]
    phone: Optional[str]
    date_of_birth: Optional[date]
    gender: Optional[GenderType]
    profile_image_url: Optional[str]
    bio: Optional[str]
    
    # Address
    address_line1: Optional[str]
    address_line2: Optional[str]
    city: Optional[str]
    state: Optional[str]
    postal_code: Optional[str]
    country: Optional[str]
    has_complete_address: bool
    
    # Social media
    tiktok_handle: Optional[str]
    discord_handle: Optional[str]
    instagram_handle: Optional[str]
    has_social_media_connected: bool
    
    # Creator specific
    content_niche: Optional[str]
    follower_count: Optional[int]
    average_views: Optional[int]
    engagement_rate: Optional[float]
    
    # Agency/Brand specific
    company_name: Optional[str]
    website_url: Optional[str]
    
    # Meta
    profile_completion_percentage: int
    timezone: str
    
    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }
    )


class UserListResponse(BaseModel):
    """Schema for paginated user list response"""
    users: List[UserResponse]
    total: int
    page: int
    per_page: int
    pages: int
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "users": [],
                "total": 100,
                "page": 1,
                "per_page": 20,
                "pages": 5
            }
        }
    )