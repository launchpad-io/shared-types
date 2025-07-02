"""
User schemas for TikTok Shop Creator CRM
Handles all user-related data validation and serialization including
profile updates, authentication, and role-specific fields.
"""

from datetime import datetime, date
from typing import Optional, Dict, List, Any, Annotated
from uuid import UUID
from enum import Enum
from decimal import Decimal
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
    country: Optional[Annotated[str, StringConstraints(min_length=2, max_length=2)]] = Field(None, description="ISO 3166-1 alpha-2 country code")

    @model_validator(mode='after')
    def validate_complete_address(self) -> 'AddressUpdate':
        """If any address field is provided, ensure minimum required fields"""
        fields = [self.address_line1, self.city, self.state, self.postal_code, self.country]
        provided = [f for f in fields if f is not None]
        
        if provided and len(provided) < 5:
            if not self.address_line1:
                raise ValueError("Address line 1 is required when updating address")
            if not self.city:
                raise ValueError("City is required when updating address")
            if not self.state:
                raise ValueError("State is required when updating address")
            if not self.postal_code:
                raise ValueError("Postal code is required when updating address")
            if not self.country:
                raise ValueError("Country is required when updating address")
        
        return self


class SocialMediaUpdate(BaseModel):
    """Schema for updating social media handles"""
    tiktok_handle: Optional[SocialHandle] = None
    discord_handle: Optional[SocialHandle] = None
    instagram_handle: Optional[SocialHandle] = None
    
    @field_validator("tiktok_handle", "discord_handle", "instagram_handle", mode='before')
    @classmethod
    def clean_handle(cls, v: Optional[str]) -> Optional[str]:
        """Remove @ symbol if present"""
        if v and v.startswith('@'):
            return v[1:]
        return v


class CreatorDetailsUpdate(BaseModel):
    """Schema for updating creator-specific details"""
    content_niche: Optional[Annotated[str, StringConstraints(min_length=3, max_length=100)]] = None
    follower_count: Optional[int] = Field(None, ge=0, le=1000000000)
    average_views: Optional[int] = Field(None, ge=0, le=1000000000)
    engagement_rate: Optional[float] = Field(None, ge=0, le=100)
    
    @field_validator("content_niche", mode='before')
    @classmethod
    def validate_niche(cls, v: Optional[str]) -> Optional[str]:
        """Validate content niche"""
        valid_niches = [
            "beauty", "fashion", "lifestyle", "food", "travel", 
            "tech", "gaming", "fitness", "education", "entertainment",
            "home", "pets", "parenting", "business", "other"
        ]
        if v and v.lower() not in valid_niches:
            raise ValueError(f"Content niche must be one of: {', '.join(valid_niches)}")
        return v.lower() if v else v


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
    country: Optional[Annotated[str, StringConstraints(min_length=2, max_length=2)]] = None
    
    # Social media
    tiktok_handle: Optional[SocialHandle] = None
    discord_handle: Optional[SocialHandle] = None
    instagram_handle: Optional[SocialHandle] = None
    
    # Creator specific
    content_niche: Optional[str] = None
    follower_count: Optional[int] = None
    average_views: Optional[int] = None
    engagement_rate: Optional[float] = None
    
    # Agency/Brand specific
    company_name: Optional[str] = None
    website_url: Optional[str] = None
    tax_id: Optional[str] = None
    
    # Preferences
    notification_preferences: Optional[NotificationPreferences] = None
    timezone: Optional[str] = None


class ProfileCompletionItem(BaseModel):
    """Schema for profile completion checklist item"""
    field_name: str
    display_name: str
    is_complete: bool
    is_required: bool
    description: Optional[str] = None


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


class UserTokenCreate(BaseModel):
    """Schema for creating user tokens"""
    user_id: UUID
    token_type: str = Field(..., description="Token type: oauth, reset_password, email_verification")
    token_value: str
    expires_at: Optional[datetime] = None


class UserTokenResponse(BaseModel):
    """Schema for user token response"""
    id: UUID
    user_id: UUID
    token_type: str
    expires_at: Optional[datetime]
    is_used: bool
    created_at: datetime
    
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat()
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
    current_gmv: Optional[float] = Field(None, description="Current total GMV")  # NEW FIELD
    
    # Agency/Brand specific
    company_name: Optional[str]
    website_url: Optional[str]
    
    # Meta
    profile_completion_percentage: int
    timezone: str
    
    # Badge summary (NEW)
    badges_earned: Optional[int] = Field(None, description="Number of badges earned")
    highest_badge: Optional[str] = Field(None, description="Highest badge achieved")
    
    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
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


class UserWithBadgesResponse(UserResponse):
    """Extended user response including badge details"""
    badges: Optional[List[Dict[str, Any]]] = Field(None, description="List of earned badges")
    badge_progress: Optional[Dict[str, Any]] = Field(None, description="Progress to next badge")
    
    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True
    )