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
    gender: Gender
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
    updated_at: Optional[datetime]  # Make this Optional to handle NULL values

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat() if v else None,
            uuid.UUID: lambda v: str(v)
        }
    )
