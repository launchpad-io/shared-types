"""
Creator-specific models for TikTok Shop Creator CRM
Handles creator badges and audience demographics.
"""

from datetime import datetime
from typing import Optional, Dict
from uuid import UUID, uuid4
from enum import Enum as PyEnum
from decimal import Decimal

from sqlalchemy import (
    Column, String, Boolean, DateTime, ForeignKey, 
    Numeric, Text, Index, CheckConstraint, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func

from app.db.base_class import Base
from app.models.user import GenderType


class BadgeType(str, PyEnum):
    """Badge type enumeration for different GMV milestones"""
    RISING_STAR = "rising_star"         # $1K
    EMERGING_CREATOR = "emerging_creator" # $5K
    ESTABLISHED = "established"         # $10K
    PROFESSIONAL = "professional"       # $25K
    EXPERT = "expert"                  # $50K
    INFLUENCER = "influencer"          # $100K
    STAR = "star"                      # $250K
    SUPERSTAR = "superstar"            # $500K
    ICON = "icon"                      # $1M


class AgeGroup(str, PyEnum):
    """Age group enumeration for audience demographics"""
    AGE_13_17 = "13-17"
    AGE_18_24 = "18-24"
    AGE_25_34 = "25-34"
    AGE_35_44 = "35-44"
    AGE_45_54 = "45-54"
    AGE_55_PLUS = "55+"


class CreatorBadge(Base):
    """
    Creator badges for achievement tracking.
    Badges are earned based on GMV milestones.
    """
    __tablename__ = "creator_badges"
    __table_args__ = (
        UniqueConstraint("creator_id", "badge_type", name="uq_creator_badge"),
        Index("idx_creator_badges_creator_id", "creator_id"),
        Index("idx_creator_badges_badge_type", "badge_type"),
        Index("idx_creator_badges_earned_at", "earned_at"),
        {"schema": "users", "extend_existing": True}
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    creator_id = Column(PGUUID(as_uuid=True), ForeignKey("users.users.id", ondelete="CASCADE"), nullable=False)
    badge_type = Column(String(50), nullable=False)
    badge_name = Column(String(100), nullable=False)
    badge_description = Column(Text)
    gmv_threshold = Column(Numeric(12, 2))
    earned_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)

    # Relationships
    creator = relationship("User", back_populates="badges")

    @validates("badge_type")
    def validate_badge_type(self, key: str, badge_type: str) -> str:
        """Validate badge type is a valid enum value"""
        valid_types = [b.value for b in BadgeType]
        if badge_type not in valid_types:
            # Also allow legacy badge types for backward compatibility
            legacy_types = ["gmv_1k", "gmv_5k", "gmv_10k", "gmv_25k", "gmv_50k", 
                          "gmv_100k", "gmv_250k", "gmv_500k", "gmv_1m"]
            if badge_type not in legacy_types:
                raise ValueError(f"Invalid badge type: {badge_type}")
        return badge_type

    @validates("gmv_threshold")
    def validate_gmv_threshold(self, key: str, threshold: Optional[Decimal]) -> Optional[Decimal]:
        """Validate GMV threshold is positive"""
        if threshold is not None and threshold < 0:
            raise ValueError("GMV threshold must be positive")
        return threshold

    @classmethod
    def get_badge_definitions(cls) -> Dict[str, Dict]:
        """
        Get all badge definitions with their thresholds and metadata.
        Returns a dictionary mapping badge types to their properties.
        """
        return {
            BadgeType.RISING_STAR: {
                "name": "Rising Star",
                "description": "Achieved $1,000 in total GMV",
                "threshold": Decimal("1000.00"),
                "tier": 1,
                "icon": "⭐",
                "color": "#CD7F32",  # Bronze
                "bg_color": "#FFF3E0"
            },
            BadgeType.EMERGING_CREATOR: {
                "name": "Emerging Creator",
                "description": "Achieved $5,000 in total GMV",
                "threshold": Decimal("5000.00"),
                "tier": 2,
                "icon": "🌟",
                "color": "#CD7F32",  # Bronze
                "bg_color": "#FFF3E0"
            },
            BadgeType.ESTABLISHED: {
                "name": "Established Creator",
                "description": "Achieved $10,000 in total GMV",
                "threshold": Decimal("10000.00"),
                "tier": 3,
                "icon": "💫",
                "color": "#C0C0C0",  # Silver
                "bg_color": "#F5F5F5"
            },
            BadgeType.PROFESSIONAL: {
                "name": "Professional",
                "description": "Achieved $25,000 in total GMV",
                "threshold": Decimal("25000.00"),
                "tier": 4,
                "icon": "✨",
                "color": "#C0C0C0",  # Silver
                "bg_color": "#F5F5F5"
            },
            BadgeType.EXPERT: {
                "name": "Expert Creator",
                "description": "Achieved $50,000 in total GMV",
                "threshold": Decimal("50000.00"),
                "tier": 5,
                "icon": "🏆",
                "color": "#FFD700",  # Gold
                "bg_color": "#FFFACD"
            },
            BadgeType.INFLUENCER: {
                "name": "Influencer",
                "description": "Achieved $100,000 in total GMV",
                "threshold": Decimal("100000.00"),
                "tier": 6,
                "icon": "👑",
                "color": "#FFD700",  # Gold
                "bg_color": "#FFFACD"
            },
            BadgeType.STAR: {
                "name": "Star Creator",
                "description": "Achieved $250,000 in total GMV",
                "threshold": Decimal("250000.00"),
                "tier": 7,
                "icon": "💎",
                "color": "#E5E4E2",  # Platinum
                "bg_color": "#F8F8FF"
            },
            BadgeType.SUPERSTAR: {
                "name": "Superstar",
                "description": "Achieved $500,000 in total GMV",
                "threshold": Decimal("500000.00"),
                "tier": 8,
                "icon": "🌠",
                "color": "#E5E4E2",  # Platinum
                "bg_color": "#F8F8FF"
            },
            BadgeType.ICON: {
                "name": "Icon",
                "description": "Achieved $1,000,000 in total GMV",
                "threshold": Decimal("1000000.00"),
                "tier": 9,
                "icon": "🔥",
                "color": "#B9F2FF",  # Diamond
                "bg_color": "#F0FFFF"
            }
        }

    def __repr__(self) -> str:
        """String representation of badge"""
        return f"<CreatorBadge(id={self.id}, type={self.badge_type}, creator={self.creator_id})>"


class CreatorAudienceDemographic(Base):
    """
    Creator audience demographics for targeting and analytics.
    Stores demographic breakdowns of a creator's audience.
    """
    __tablename__ = "creator_audience_demographics"
    __table_args__ = (
        UniqueConstraint("creator_id", "age_group", "gender", "country", 
                        name="uq_creator_demographic"),
        Index("idx_audience_demographics_creator_id", "creator_id"),
        CheckConstraint("percentage >= 0 AND percentage <= 100", 
                       name="check_demographic_percentage"),
        {"schema": "users", "extend_existing": True}
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    creator_id = Column(PGUUID(as_uuid=True), ForeignKey("users.users.id", ondelete="CASCADE"), nullable=False)
    age_group = Column(String(20), nullable=False)
    gender = Column(String(20), nullable=False)
    percentage = Column(Numeric(5, 2), nullable=False)
    country = Column(String(100))
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    creator = relationship("User", back_populates="audience_demographics")

    @validates("age_group")
    def validate_age_group(self, key: str, age_group: str) -> str:
        """Validate age group is a valid enum value"""
        if age_group not in [a.value for a in AgeGroup]:
            raise ValueError(f"Invalid age group: {age_group}")
        return age_group

    @validates("gender")
    def validate_gender(self, key: str, gender: str) -> str:
        """Validate gender is a valid enum value"""
        valid_genders = [g.value for g in GenderType]
        # Also allow 'all' for aggregate demographics
        if gender not in valid_genders and gender != 'all':
            raise ValueError(f"Invalid gender: {gender}")
        return gender

    @validates("percentage")
    def validate_percentage(self, key: str, percentage: Decimal) -> Decimal:
        """Validate percentage is within valid range"""
        if percentage < 0 or percentage > 100:
            raise ValueError("Percentage must be between 0 and 100")
        return percentage

    @validates("country")
    def validate_country(self, key: str, country: Optional[str]) -> Optional[str]:
        """Validate and format country code"""
        if country:
            # Ensure country code is uppercase and 2-3 characters
            country = country.upper().strip()
            if len(country) < 2 or len(country) > 3:
                raise ValueError("Country code must be 2-3 characters")
            return country
        return country

    def __repr__(self) -> str:
        """String representation of demographic"""
        return (f"<CreatorAudienceDemographic(id={self.id}, "
                f"creator={self.creator_id}, "
                f"age={self.age_group}, "
                f"gender={self.gender}, "
                f"percentage={self.percentage}%)>")