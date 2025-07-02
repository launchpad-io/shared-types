"""
Creator-specific schemas for TikTok Shop Creator CRM
Handles creator badges, audience demographics, and performance metrics.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict, EmailStr

from app.models.user import GenderType


# Import badge schemas from the new badge module
from app.schemas.badge import (
    BadgeResponse,
    BadgeProgressResponse,
    BadgeHistoryResponse,
    PaceEstimateResponse,
    BadgeShowcaseResponse
)


class AgeGroup(str, Enum):
    """Age group enumeration for audience demographics"""
    AGE_13_17 = "13-17"
    AGE_18_24 = "18-24"
    AGE_25_34 = "25-34"
    AGE_35_44 = "35-44"
    AGE_45_54 = "45-54"
    AGE_55_PLUS = "55+"


class AudienceDemographicCreate(BaseModel):
    """Schema for creating audience demographic entry"""
    age_group: AgeGroup
    gender: GenderType
    percentage: float = Field(..., ge=0, le=100, description="Percentage of audience")
    country: Optional[str] = Field(None, max_length=100)
    
    model_config = ConfigDict(use_enum_values=True)


class AudienceDemographicResponse(BaseModel):
    """Schema for audience demographic response"""
    id: UUID
    creator_id: UUID
    age_group: str
    gender: str
    percentage: float
    country: Optional[str]
    updated_at: datetime
    
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )


class AudienceDemographicsBulkUpdate(BaseModel):
    """Schema for bulk updating audience demographics"""
    demographics: List[AudienceDemographicCreate]
    
    @model_validator(mode='after')
    def validate_percentages(self) -> 'AudienceDemographicsBulkUpdate':
        """Ensure percentages sum to approximately 100%"""
        total = sum(d.percentage for d in self.demographics)
        if abs(total - 100) > 0.1:  # Allow 0.1% tolerance for rounding
            raise ValueError(f"Demographics percentages must sum to 100%, got {total}%")
        return self


class CreatorPerformanceMetrics(BaseModel):
    """Schema for creator performance metrics"""
    creator_id: UUID
    total_gmv: float = Field(..., ge=0, description="Total GMV generated")
    average_order_value: float = Field(..., ge=0, description="Average order value")
    conversion_rate: float = Field(..., ge=0, le=100, description="Conversion rate percentage")
    total_orders: int = Field(..., ge=0, description="Total number of orders")
    total_campaigns: int = Field(..., ge=0, description="Total campaigns participated")
    active_campaigns: int = Field(..., ge=0, description="Currently active campaigns")
    completion_rate: float = Field(..., ge=0, le=100, description="Campaign completion rate")
    avg_engagement_rate: float = Field(..., ge=0, le=100, description="Average engagement rate")
    
    # Badge summary
    badges_earned: int = Field(..., ge=0, description="Number of badges earned")
    highest_badge: Optional[str] = Field(None, description="Highest badge achieved")
    next_badge_progress: Optional[float] = Field(None, ge=0, le=100, description="Progress to next badge")
    
    # Time-based metrics
    gmv_last_30_days: float = Field(..., ge=0, description="GMV in last 30 days")
    gmv_growth_rate: float = Field(..., description="GMV growth rate percentage")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            Decimal: lambda v: float(v)
        }
    )


class CreatorRankingResponse(BaseModel):
    """Schema for creator ranking/leaderboard entry"""
    rank: int = Field(..., ge=1, description="Creator's rank")
    creator_id: UUID
    username: str
    profile_image_url: Optional[str]
    total_gmv: float = Field(..., ge=0)
    badges_earned: int = Field(..., ge=0)
    highest_badge: Optional[str]
    content_niche: Optional[str]
    follower_count: Optional[int]
    change_in_rank: Optional[int] = Field(None, description="Change from previous period")
    
    model_config = ConfigDict(from_attributes=True)


class CreatorLeaderboardResponse(BaseModel):
    """Schema for creator leaderboard"""
    period: str = Field(..., description="Leaderboard period (weekly, monthly, all-time)")
    updated_at: datetime
    total_creators: int
    leaderboard: List[CreatorRankingResponse]
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )


class CreatorAnalyticsSummary(BaseModel):
    """Schema for creator analytics summary"""
    creator_id: UUID
    period_start: datetime
    period_end: datetime
    
    # Performance metrics
    total_gmv: float = Field(..., ge=0)
    total_orders: int = Field(..., ge=0)
    average_order_value: float = Field(..., ge=0)
    conversion_rate: float = Field(..., ge=0, le=100)
    
    # Engagement metrics
    total_views: int = Field(..., ge=0)
    total_clicks: int = Field(..., ge=0)
    engagement_rate: float = Field(..., ge=0, le=100)
    
    # Campaign metrics
    campaigns_participated: int = Field(..., ge=0)
    campaigns_completed: int = Field(..., ge=0)
    deliverables_submitted: int = Field(..., ge=0)
    deliverables_approved: int = Field(..., ge=0)
    
    # Growth metrics
    gmv_growth: float = Field(..., description="GMV growth percentage")
    follower_growth: float = Field(..., description="Follower growth percentage")
    engagement_growth: float = Field(..., description="Engagement growth percentage")
    
    # Top performing content
    top_products: List[Dict[str, Any]] = Field(default_factory=list)
    top_campaigns: List[Dict[str, Any]] = Field(default_factory=list)
    
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }
    )


class CreatorProfileResponse(BaseModel):
    """Comprehensive creator profile response"""
    # Basic info
    id: UUID
    username: str
    email: EmailStr
    first_name: Optional[str]
    last_name: Optional[str]
    profile_image_url: Optional[str]
    bio: Optional[str]
    
    # Creator stats
    content_niche: Optional[str]
    follower_count: Optional[int]
    average_views: Optional[int]
    engagement_rate: Optional[float]
    current_gmv: float = Field(..., description="Current total GMV")
    
    # Social media
    tiktok_handle: Optional[str]
    instagram_handle: Optional[str]
    discord_handle: Optional[str]
    
    # Badge information
    badges: List[BadgeResponse] = Field(default_factory=list)
    badge_progress: Optional[BadgeProgressResponse] = None
    
    # Performance summary
    total_campaigns: int = Field(0, description="Total campaigns participated")
    completion_rate: float = Field(0.0, description="Campaign completion rate")
    avg_rating: Optional[float] = Field(None, description="Average rating from brands")
    
    # Account info
    created_at: datetime
    last_active: Optional[datetime]
    is_verified: bool = Field(False, description="Verified creator status")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }
    )