# app/schemas/demographics.py
"""
Pydantic schemas for demographics endpoints
Compatible with Pydantic v2
"""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime
import uuid
from enum import Enum


class AgeGroup(str, Enum):
    """Age group enum"""
    AGE_13_17 = "13-17"
    AGE_18_24 = "18-24"
    AGE_25_34 = "25-34"
    AGE_35_44 = "35-44"
    AGE_45_54 = "45-54"
    AGE_55_PLUS = "55+"


class Gender(str, Enum):
    """Gender enum"""
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    NOT_SPECIFIED = "not_specified"


class DemographicsBase(BaseModel):
    """Base demographics schema"""
    age_group: AgeGroup
    gender: Gender  # Added gender field since your router expects it
    percentage: Decimal = Field(..., ge=0, le=100)
    country: Optional[str] = Field(None, max_length=100)

    @field_validator('percentage', mode='before')
    @classmethod
    def round_percentage(cls, v):
        if v is not None:
            return round(Decimal(str(v)), 2)
        return v

    @field_validator('country')
    @classmethod
    def clean_country(cls, v):
        if v is not None and v.strip() == '':
            return None
        return v

    model_config = ConfigDict(
        json_encoders={
            Decimal: lambda v: float(v)
        }
    )


class DemographicsCreate(DemographicsBase):
    """Schema for creating demographics - no creator_id needed"""
    pass


class DemographicsCreateWithCreator(DemographicsBase):
    """Schema for creating demographics with explicit creator_id"""
    creator_id: uuid.UUID


class DemographicsUpdate(BaseModel):
    """Schema for updating demographics"""
    age_group: Optional[AgeGroup] = None
    gender: Optional[Gender] = None
    percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    country: Optional[str] = Field(None, max_length=100)

    @field_validator('percentage', mode='before')
    @classmethod
    def round_percentage(cls, v):
        if v is not None:
            return round(Decimal(str(v)), 2)
        return v

    model_config = ConfigDict(
        json_encoders={
            Decimal: lambda v: float(v)
        }
    )


class DemographicsResponse(DemographicsBase):
    """Response schema for demographics"""
    id: uuid.UUID
    creator_id: uuid.UUID
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,  # This replaces orm_mode in Pydantic v2
        json_encoders={
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }
    )


class DemographicsEntry(DemographicsBase):
    """Schema for bulk operations without creator_id"""
    pass


class DemographicsBulkCreate(BaseModel):
    """Schema for bulk creating demographics"""
    demographics: List[DemographicsEntry]
    
    @field_validator('demographics')
    @classmethod
    def validate_demographics_list(cls, v):
        if not v:
            raise ValueError('Demographics list cannot be empty')
        if len(v) > 100:
            raise ValueError('Cannot create more than 100 demographics entries at once')
        
        # Validate no duplicate entries
        seen = set()
        for demo in v:
            key = (demo.age_group, demo.gender, demo.country)
            if key in seen:
                raise ValueError(f'Duplicate entry found for {demo.age_group}/{demo.gender}/{demo.country or "ALL"}')
            seen.add(key)
        
        # Validate total percentage per age_group/gender combination
        totals = {}
        for demo in v:
            key = (demo.age_group, demo.gender)
            totals[key] = totals.get(key, Decimal('0')) + demo.percentage
        
        for key, total in totals.items():
            if total > Decimal('100'):
                age_group, gender = key
                raise ValueError(f'Total percentage for {age_group}/{gender} exceeds 100% (total: {total}%)')
        
        return v

    model_config = ConfigDict(
        json_encoders={
            Decimal: lambda v: float(v)
        }
    )


class DemographicsSummary(BaseModel):
    """Summary statistics for creator demographics"""
    creator_id: uuid.UUID
    total_entries: int
    total_percentage: Decimal
    age_distribution: Dict[str, Decimal]
    gender_distribution: Dict[str, Decimal]
    country_distribution: Dict[str, Decimal]
    last_updated: Optional[datetime]

    model_config = ConfigDict(
        json_encoders={
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat() if v else None
        }
    )


class DemographicsComparisonResult(BaseModel):
    """Result of comparing demographics between creators"""
    creator_id_1: uuid.UUID
    creator_id_2: uuid.UUID
    overlap_percentage: float
    unique_segments_creator1: int
    unique_segments_creator2: int
    shared_segments: int
    detailed_overlap: Dict[str, Dict[str, float]]


class DemographicsInsight(BaseModel):
    """Analytics insights for demographics"""
    creator_id: uuid.UUID
    primary_audience: Dict[str, str]
    audience_concentration: float
    top_segments: List[Dict[str, Any]]
    growth_segments: List[Dict[str, Any]]
    recommendations: List[str]


class DemographicsFilter(BaseModel):
    """Filter parameters for searching demographics"""
    age_groups: Optional[List[AgeGroup]] = None
    genders: Optional[List[Gender]] = None
    countries: Optional[List[str]] = None
    min_percentage: Optional[float] = Field(None, ge=0, le=100)
    max_percentage: Optional[float] = Field(None, ge=0, le=100)
    creator_ids: Optional[List[uuid.UUID]] = None

    @field_validator('max_percentage')
    @classmethod
    def validate_percentage_range(cls, v, info):
        if v is not None and info.data.get('min_percentage') is not None:
            if v < info.data['min_percentage']:
                raise ValueError('max_percentage must be greater than min_percentage')
        return v