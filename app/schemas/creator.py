"""
Creator-specific schemas for TikTok Shop Creator CRM
Handles creator badges, audience demographics, and performance metrics.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import Annotated
from pydantic import StringConstraints

from app.models.creator import BadgeType, AgeGroup
from app.models.user import GenderType


class BadgeInfo(BaseModel):
    """Schema for badge information"""
    badge_type: BadgeType
    name: str
    description: str
    threshold: Decimal
    color: str = Field(..., description="Badge color: bronze, silver, gold, platinum, diamond")
    
    model_config = ConfigDict(
        use_enum_values=True,
        json_encoders={
            Decimal: str
        }
    )


class CreatorBadgeResponse(BaseModel):
    """Schema for creator badge response"""
    id: UUID
    badge_type: str
    badge_name: str
    badge_description: Optional[str]
    gmv_threshold: Decimal
    earned_at: datetime
    is_active: bool
    
    # Additional computed fields
    color: Optional[str] = None
    next_threshold: Optional[Decimal] = None
    progress_to_next: Optional[float] = None
    
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            Decimal: str
        }
    )


class BadgeProgressResponse(BaseModel):
    """Schema for badge progress tracking"""
    badge_type: BadgeType
    badge_name: str
    description: str
    threshold: Decimal
    color: str
    earned: bool
    earned_at: Optional[datetime] = None
    current_gmv: Decimal
    progress_percentage: float = Field(..., ge=0, le=100)
    gmv_needed: Optional[Decimal] = None
    
    model_config = ConfigDict(
        use_enum_values=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            Decimal: str
        },
        json_schema_extra={
            "example": {
                "badge_type": "gmv_10k",
                "badge_name": "$10K GMV Badge",
                "description": "Achieved $10,000 in total GMV",
                "threshold": "10000.00",
                "color": "silver",
                "earned": False,
                "earned_at": None,
                "current_gmv": "7500.00",
                "progress_percentage": 75.0,
                "gmv_needed": "2500.00"
            }
        }
    )


class AllBadgesProgressResponse(BaseModel):
    """Schema for all badges progress response"""
    total_gmv: Decimal
    badges_earned: int
    badges_available: int
    next_badge: Optional[BadgeProgressResponse] = None
    all_badges: List[BadgeProgressResponse]
    
    model_config = ConfigDict(
        json_encoders={
            Decimal: str
        }
    )


class AudienceDemographicCreate(BaseModel):
    """Schema for creating/updating audience demographics"""
    age_group: AgeGroup
    gender: GenderType
    percentage: Annotated[float, Field(ge=0, le=100)]
    country: Optional[str] = Field(None, min_length=2, max_length=3)
    
    @field_validator("country")
    @classmethod
    def validate_country(cls, v: Optional[str]) -> Optional[str]:
        """Ensure country code is uppercase"""
        if v:
            return v.upper()
        return v
    
    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "age_group": "18-24",
                "gender": "female",
                "percentage": 35.5,
                "country": "US"
            }
        }
    )


class AudienceDemographicResponse(BaseModel):
    """Schema for audience demographic response"""
    id: UUID
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
    def validate_demographics(self) -> 'AudienceDemographicsBulkUpdate':
        """Validate demographic data integrity"""
        demographics = self.demographics
        
        if not demographics:
            raise ValueError("At least one demographic entry is required")
        
        # Group by gender and sum percentages
        gender_totals: Dict[str, float] = {}
        for demo in demographics:
            gender = demo.gender
            percentage = demo.percentage
            gender_totals[gender] = gender_totals.get(gender, 0) + percentage
        
        # Validate that percentages sum to approximately 100% per gender
        for gender, total in gender_totals.items():
            if abs(total - 100.0) > 0.1:  # Allow 0.1% tolerance for floating point
                raise ValueError(
                    f"Percentages for gender '{gender}' must sum to 100% (current: {total}%)"
                )
        
        return self
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "demographics": [
                    {"age_group": "18-24", "gender": "female", "percentage": 45.0, "country": "US"},
                    {"age_group": "25-34", "gender": "female", "percentage": 35.0, "country": "US"},
                    {"age_group": "35-44", "gender": "female", "percentage": 20.0, "country": "US"},
                    {"age_group": "18-24", "gender": "male", "percentage": 60.0, "country": "US"},
                    {"age_group": "25-34", "gender": "male", "percentage": 40.0, "country": "US"}
                ]
            }
        }
    )


class CreatorPerformanceMetrics(BaseModel):
    """Schema for creator performance metrics"""
    total_gmv: Decimal
    total_orders: int
    average_order_value: Decimal
    conversion_rate: float
    engagement_rate: float
    total_campaigns: int
    active_campaigns: int
    completed_campaigns: int
    average_campaign_gmv: Decimal
    best_performing_niche: Optional[str]
    performance_trend: str = Field(..., description="trending_up, stable, trending_down")
    
    model_config = ConfigDict(
        json_encoders={
            Decimal: str
        },
        json_schema_extra={
            "example": {
                "total_gmv": "125000.00",
                "total_orders": 2500,
                "average_order_value": "50.00",
                "conversion_rate": 3.5,
                "engagement_rate": 5.2,
                "total_campaigns": 15,
                "active_campaigns": 3,
                "completed_campaigns": 12,
                "average_campaign_gmv": "8333.33",
                "best_performing_niche": "fashion",
                "performance_trend": "trending_up"
            }
        }
    )


class CreatorRankingResponse(BaseModel):
    """Schema for creator ranking/leaderboard response"""
    creator_id: UUID
    username: str
    profile_image_url: Optional[str]
    total_gmv: Decimal
    rank: int
    percentile: float = Field(..., ge=0, le=100)
    movement: int = Field(..., description="Position change from last period")
    badges_earned: int
    top_badge: Optional[str]
    
    model_config = ConfigDict(
        json_encoders={
            Decimal: str
        }
    )


class CreatorLeaderboardResponse(BaseModel):
    """Schema for creator leaderboard response"""
    period: str = Field(..., description="daily, weekly, monthly, all_time")
    total_creators: int
    your_ranking: Optional[CreatorRankingResponse]
    top_creators: List[CreatorRankingResponse]
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "period": "monthly",
                "total_creators": 5000,
                "your_ranking": {
                    "creator_id": "123e4567-e89b-12d3-a456-426614174000",
                    "username": "creator123",
                    "profile_image_url": "https://example.com/image.jpg",
                    "total_gmv": "15000.00",
                    "rank": 42,
                    "percentile": 99.2,
                    "movement": 5,
                    "badges_earned": 3,
                    "top_badge": "gmv_10k"
                },
                "top_creators": []
            }
        }
    )


class CreatorAnalyticsSummary(BaseModel):
    """Schema for creator analytics summary"""
    performance_metrics: CreatorPerformanceMetrics
    audience_demographics: List[AudienceDemographicResponse]
    badge_progress: AllBadgesProgressResponse
    ranking: CreatorRankingResponse
    
    model_config = ConfigDict(
        json_schema_extra={
            "description": "Comprehensive analytics summary for a creator"
        }
    )