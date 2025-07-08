"""
Badge Schemas
Pydantic v2 models for badge-related data
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, field_validator


class BadgeBase(BaseModel):
    """Base badge schema"""
    badge_type: str = Field(..., description="Type of badge (e.g., 'rising_star')")
    badge_name: str = Field(..., description="Display name of the badge")
    badge_description: Optional[str] = Field(None, description="Badge description")
    gmv_threshold: Optional[float] = Field(None, description="GMV required for this badge")


class BadgeCreate(BadgeBase):
    """Schema for creating a badge"""
    creator_id: UUID = Field(..., description="UUID of the creator")


class BadgeResponse(BaseModel):
    """Badge response with full details"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(..., description="Badge identifier")
    badge_type: str = Field(..., description="Type of badge")
    name: str = Field(..., description="Display name")
    description: str = Field(..., description="Badge description")
    tier: str = Field(..., description="Badge tier (Bronze, Silver, etc.)")
    gmv_requirement: float = Field(..., description="GMV required")
    status: str = Field(..., description="Status: earned, in-progress, locked")
    progress: float = Field(0.0, ge=0, le=100, description="Progress percentage")
    earned_date: Optional[datetime] = Field(None, description="Date earned")
    icon: str = Field(..., description="Icon identifier")
    color: str = Field(..., description="Color class")
    bg_color: str = Field(..., description="Background color class")


class BadgeProgressResponse(BaseModel):
    """Overall badge progress for a creator"""
    model_config = ConfigDict(from_attributes=True)
    
    creator_id: UUID
    current_gmv: float = Field(..., ge=0, description="Current total GMV")
    total_badges_earned: int = Field(..., ge=0, description="Number of badges earned")
    total_badges_available: int = Field(..., ge=0, description="Total badges available")
    next_badge_type: Optional[str] = Field(None, description="Next badge to earn")
    next_badge_name: Optional[str] = Field(None, description="Name of next badge")
    next_badge_threshold: Optional[float] = Field(None, description="GMV needed for next badge")
    progress_percentage: float = Field(..., ge=0, le=100, description="Progress to next badge")
    remaining_gmv: float = Field(..., ge=0, description="GMV remaining to next badge")
    current_badge_type: Optional[str] = Field(None, description="Current highest badge")
    current_badge_name: Optional[str] = Field(None, description="Name of current badge")


class ProgressDetails(BaseModel):
    """Detailed progress for a specific badge"""
    model_config = ConfigDict(from_attributes=True)
    
    badge_type: str
    badge_name: str
    is_earned: bool = Field(..., description="Whether badge is earned")
    earned_date: Optional[datetime] = None
    progress_percentage: float = Field(..., ge=0, le=100)
    current_value: float = Field(..., ge=0, description="Current GMV")
    threshold_value: float = Field(..., ge=0, description="Required GMV")
    remaining_value: float = Field(..., ge=0, description="GMV remaining")


class BadgeHistoryResponse(BaseModel):
    """Badge achievement history entry"""
    model_config = ConfigDict(from_attributes=True)
    
    date: datetime = Field(..., description="Achievement date")
    badge_name: str
    badge_type: str
    gmv_at_time: float = Field(..., ge=0, description="GMV when earned")
    message: str = Field(..., description="Achievement message")
    icon: str
    color: str


class BadgeStatsResponse(BaseModel):
    """Network-wide badge statistics"""
    model_config = ConfigDict(from_attributes=True)
    
    total_badges_earned: int = Field(..., ge=0)
    creators_with_badges: int = Field(..., ge=0)
    badge_distribution: Dict[str, Dict[str, Any]] = Field(
        ..., 
        description="Distribution of badges by type"
    )


class PaceEstimateResponse(BaseModel):
    """Pace estimate for achieving a badge"""
    model_config = ConfigDict(from_attributes=True)
    
    badge_type: str
    badge_name: str
    is_achieved: bool
    current_gmv: float = Field(..., ge=0)
    target_gmv: float = Field(..., ge=0)
    remaining_gmv: Optional[float] = Field(None, ge=0)
    days_to_achieve: Optional[int] = Field(None, description="Estimated days to achieve")
    estimated_date: Optional[datetime] = Field(None, description="Estimated achievement date")
    daily_average_needed: float = Field(..., ge=0, description="Daily GMV needed")
    current_daily_average: float = Field(..., ge=0, description="Current daily average")
    confidence_level: str = Field(..., description="Confidence in estimate")
    pace_breakdown: Optional[Dict[str, float]] = Field(
        None, 
        description="Daily GMV needed for different timeframes"
    )


class BadgeShowcaseResponse(BaseModel):
    """Badge showcase for profile display"""
    model_config = ConfigDict(from_attributes=True)
    
    featured_badges: List[BadgeResponse] = Field(
        ..., 
        description="Featured badges to display"
    )
    total_earned: int = Field(..., ge=0)
    highest_tier: Optional[str] = Field(None, description="Highest badge tier earned")
    recent_achievement: Optional[BadgeHistoryResponse] = Field(
        None, 
        description="Most recent badge earned"
    )


class CreatorBadgesSummary(BaseModel):
    """Summary of creator's badges for listings"""
    model_config = ConfigDict(from_attributes=True)
    
    creator_id: UUID
    username: str
    total_gmv: float = Field(..., ge=0)
    badges_earned: int = Field(..., ge=0)
    highest_badge: Optional[str] = None
    badges: List[str] = Field(default_factory=list, description="List of badge types earned")