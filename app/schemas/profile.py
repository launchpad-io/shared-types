"""
Profile-specific schemas for TikTok Shop Creator CRM
Dedicated schemas for profile completion and updates
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, validator, root_validator


class ProfileSection(str, Enum):
    """Profile section types"""
    BASIC = "basic"
    PERSONAL = "personal"
    ADDRESS = "address"
    SOCIAL = "social"
    CREATOR_DETAILS = "creator_details"
    COMPANY_DETAILS = "company_details"


class ProfileFieldStatus(BaseModel):
    """Status of individual profile field"""
    field_name: str
    display_name: str
    is_complete: bool
    current_value: Optional[Any] = None
    field_type: str = Field(..., description="text, date, select, url, etc.")
    is_required: bool = True
    validation_message: Optional[str] = None


class ProfileSectionStatus(BaseModel):
    """Status of a profile section"""
    section: ProfileSection
    name: str
    description: str
    completion_percentage: float = Field(..., ge=0, le=100)
    total_fields: int
    completed_fields: int
    fields: List[ProfileFieldStatus]
    is_applicable: bool = True


class ProfileCompletionDetail(BaseModel):
    """Detailed profile completion information"""
    overall_percentage: int = Field(..., ge=0, le=100)
    sections: List[ProfileSectionStatus]
    missing_required_fields: List[str]
    suggested_actions: List[str]
    last_updated: datetime
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ProfileUpdateResult(BaseModel):
    """Result of profile update operation"""
    success: bool
    updated_fields: List[str]
    validation_errors: Optional[Dict[str, str]] = None
    new_completion_percentage: int
    message: str


class BulkProfileUpdate(BaseModel):
    """Schema for bulk profile updates with validation"""
    updates: Dict[str, Any]
    validate_only: bool = False
    
    @validator("updates")
    def validate_updates(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure no system fields are being updated"""
        protected_fields = {
            'id', 'email', 'username', 'hashed_password', 
            'created_at', 'updated_at', 'role'
        }
        
        invalid_fields = set(v.keys()) & protected_fields
        if invalid_fields:
            raise ValueError(f"Cannot update protected fields: {', '.join(invalid_fields)}")
        
        return v


class ProfileVerificationRequest(BaseModel):
    """Request for profile verification (phone, email, etc.)"""
    verification_type: str = Field(..., regex="^(phone|email|tiktok|discord)$")
    value: str
    send_code: bool = True


class ProfileVerificationConfirm(BaseModel):
    """Confirm profile verification"""
    verification_type: str = Field(..., regex="^(phone|email|tiktok|discord)$")
    code: str = Field(..., min_length=6, max_length=6)


class ProfileExportRequest(BaseModel):
    """Request to export profile data (GDPR compliance)"""
    format: str = Field("json", regex="^(json|csv|pdf)$")
    include_sections: List[ProfileSection] = Field(
        default_factory=lambda: list(ProfileSection)
    )
    include_activity_log: bool = False


class ProfileImportData(BaseModel):
    """Schema for importing profile data"""
    source: str = Field(..., description="Source of import: tiktok, instagram, etc.")
    data: Dict[str, Any]
    overwrite_existing: bool = False
    
    @root_validator
    def validate_import_data(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Validate import data based on source"""
        source = values.get("source")
        data = values.get("data", {})
        
        if source == "tiktok":
            required_fields = ["username", "follower_count"]
            missing = [f for f in required_fields if f not in data]
            if missing:
                raise ValueError(f"Missing required fields for TikTok import: {', '.join(missing)}")
        
        return values


class ProfileMergeRequest(BaseModel):
    """Request to merge duplicate profiles"""
    primary_profile_id: UUID
    secondary_profile_id: UUID
    merge_strategy: str = Field("primary_wins", regex="^(primary_wins|secondary_wins|newest_wins|manual)$")
    field_mappings: Optional[Dict[str, str]] = None


class ProfileCompletionIncentive(BaseModel):
    """Incentive for profile completion"""
    milestone_percentage: int = Field(..., ge=0, le=100)
    reward_type: str = Field(..., description="badge, credit, feature_unlock")
    reward_value: str
    achieved: bool = False
    achieved_at: Optional[datetime] = None


class ProfileCompletionCampaign(BaseModel):
    """Campaign to encourage profile completion"""
    campaign_id: UUID
    name: str
    description: str
    start_date: datetime
    end_date: datetime
    target_completion: int = Field(..., ge=0, le=100)
    incentives: List[ProfileCompletionIncentive]
    is_active: bool = True


class ProfileAnalytics(BaseModel):
    """Analytics for profile views and interactions"""
    profile_views_total: int
    profile_views_this_month: int
    profile_completion_trend: List[Dict[str, Any]]  # Array of {date, percentage}
    most_viewed_sections: List[str]
    average_time_to_complete: Optional[int] = Field(None, description="Minutes")
    conversion_to_campaign: float = Field(..., ge=0, le=100)