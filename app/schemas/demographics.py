"""
Demographics Schemas
Pydantic models for demographics-specific endpoints
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict, field_validator


class DemographicsTemplateFormat(str, Enum):
    """Template format options"""
    csv = "csv"
    xlsx = "xlsx"


class DemographicsImportResponse(BaseModel):
    """Response for demographics import"""
    success: bool
    imported_count: int = Field(..., ge=0)
    error_count: int = Field(..., ge=0)
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    message: str
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "imported_count": 10,
                "error_count": 2,
                "errors": [
                    {
                        "row": 5,
                        "errors": [{"msg": "Invalid age group: 12-16"}]
                    }
                ],
                "message": "Successfully imported 10 demographics"
            }
        }
    )


class GenderDistributionData(BaseModel):
    """Gender distribution for charts"""
    name: str
    value: float = Field(..., ge=0, le=100)
    color: str


class AgeDistributionData(BaseModel):
    """Age distribution for charts"""
    age_group: str
    percentage: float = Field(..., ge=0, le=100)
    color: str


class LocationDistributionData(BaseModel):
    """Location distribution data"""
    country: str
    country_name: str
    percentage: float = Field(..., ge=0, le=100)


class DemographicBreakdown(BaseModel):
    """Detailed demographic segment"""
    segment: str
    country: str
    percentage: float = Field(..., ge=0, le=100)
    gender: str
    age_group: str


class DemographicsVisualizationResponse(BaseModel):
    """Complete visualization data response"""
    gender_distribution: Dict[str, Any] = Field(
        ...,
        description="Gender distribution with chart data"
    )
    age_distribution: Dict[str, Any] = Field(
        ...,
        description="Age distribution with chart data"
    )
    location_distribution: Dict[str, Any] = Field(
        ...,
        description="Location distribution with top countries"
    )
    detailed_breakdown: List[DemographicBreakdown] = Field(
        default_factory=list,
        description="Top demographic segments"
    )
    has_demographics: bool
    last_updated: Optional[datetime] = None
    
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        }
    )


class DemographicsSearchFilters(BaseModel):
    """Filters for searching creators by demographics"""
    age_groups: Optional[List[str]] = Field(None, description="Filter by age groups")
    genders: Optional[List[str]] = Field(None, description="Filter by genders")
    countries: Optional[List[str]] = Field(None, description="Filter by countries")
    min_percentage: Optional[float] = Field(
        None, 
        ge=0, 
        le=100,
        description="Minimum percentage for any demographic"
    )
    
    @field_validator('age_groups', 'genders')
    @classmethod
    def validate_list_not_empty(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None and len(v) == 0:
            return None
        return v


class DemographicsAnalyticsResponse(BaseModel):
    """Aggregated analytics across creators"""
    total_creators: int = Field(..., ge=0)
    gender_distribution: Dict[str, float] = Field(
        ...,
        description="Average gender distribution across network"
    )
    age_distribution: Dict[str, float] = Field(
        ...,
        description="Average age distribution across network"
    )
    top_countries: List[tuple[str, float]] = Field(
        default_factory=list,
        description="Most common countries across network"
    )
    average_metrics: Dict[str, float] = Field(
        ...,
        description="Average demographic metrics"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_creators": 150,
                "gender_distribution": {
                    "female": 65.5,
                    "male": 34.5
                },
                "age_distribution": {
                    "18-24": 45.0,
                    "25-34": 35.0,
                    "35-44": 20.0
                },
                "top_countries": [
                    ["US", 78.5],
                    ["CA", 12.3],
                    ["GB", 9.2]
                ],
                "average_metrics": {
                    "avg_female_percentage": 65.5,
                    "avg_youth_percentage": 45.0,
                    "avg_countries_per_creator": 1.8
                }
            }
        }
    )


class DemographicsComparisonRequest(BaseModel):
    """Request for comparing multiple creators"""
    creator_ids: List[UUID] = Field(
        ...,
        min_length=2,
        max_length=5,
        description="List of creator IDs to compare"
    )


class CreatorComparisonData(BaseModel):
    """Comparison data for a single creator"""
    creator_id: str
    data: Dict[str, float]


class DemographicsComparisonResponse(BaseModel):
    """Response for demographics comparison"""
    creators: List[Any] = Field(default_factory=list)
    gender_comparison: List[CreatorComparisonData]
    age_comparison: List[CreatorComparisonData]
    location_overlap: List[Any] = Field(default_factory=list)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "creators": [],
                "gender_comparison": [
                    {
                        "creator_id": "123e4567-e89b-12d3-a456-426614174000",
                        "data": {"Female": 67.5, "Male": 32.5}
                    }
                ],
                "age_comparison": [
                    {
                        "creator_id": "123e4567-e89b-12d3-a456-426614174000",
                        "data": {"18-24": 45.0, "25-34": 35.0}
                    }
                ],
                "location_overlap": []
            }
        }
    )


class DemographicsSummaryResponse(BaseModel):
    """Quick summary of creator demographics"""
    has_demographics: bool
    gender_distribution: Dict[str, float] = Field(
        default_factory=dict,
        description="Gender percentages"
    )
    age_distribution: Dict[str, float] = Field(
        default_factory=dict,
        description="Age group percentages"
    )
    top_countries: List[tuple[str, float]] = Field(
        default_factory=list,
        description="Top countries with percentages"
    )
    primary_audience: Optional[Dict[str, Any]] = Field(
        None,
        description="Primary demographic segment"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "has_demographics": True,
                "gender_distribution": {
                    "female": 67.5,
                    "male": 32.5
                },
                "age_distribution": {
                    "18-24": 45.0,
                    "25-34": 35.0,
                    "35-44": 20.0
                },
                "top_countries": [
                    ["US", 78.5],
                    ["CA", 12.3]
                ],
                "primary_audience": {
                    "age_group": "18-24",
                    "gender": "female",
                    "percentage": 30.5
                }
            }
        }
    )


class DemographicsExportRequest(BaseModel):
    """Request for exporting demographics"""
    creator_ids: Optional[List[UUID]] = Field(
        None,
        description="Specific creators to export (admin only)"
    )
    format: DemographicsTemplateFormat = Field(
        DemographicsTemplateFormat.csv,
        description="Export format"
    )
    include_summary: bool = Field(
        False,
        description="Include summary statistics"
    )


class DemographicsTrendData(BaseModel):
    """Demographics trend over time"""
    date: datetime
    gender_distribution: Dict[str, float]
    age_distribution: Dict[str, float]
    total_reach: int = Field(..., ge=0)
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )