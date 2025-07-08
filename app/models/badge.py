"""
Creator Badge Model
Maps to the users.creator_badges table
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
from decimal import Decimal

from sqlalchemy import (
    Column, String, Boolean, DateTime, 
    Numeric, Text, ForeignKey, Index
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base_class import Base


class CreatorBadge(Base):
    """
    Model for creator badges/achievements
    Maps to existing users.creator_badges table
    """
    __tablename__ = "creator_badges"
    __table_args__ = (
        Index("idx_creator_badges_creator_id", "creator_id"),
        Index("idx_creator_badges_badge_type", "badge_type"),
        Index("idx_creator_badges_earned_at", "earned_at"),
        {"schema": "users", "extend_existing": True}
    )

    # Primary Key
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Foreign Key to users
    creator_id = Column(
        PGUUID(as_uuid=True), 
        ForeignKey("users.users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Badge Information
    badge_type = Column(String(50), nullable=False)  # 'rising_star', 'emerging_creator', etc.
    badge_name = Column(String(100), nullable=False)  # Display name
    badge_description = Column(Text)
    gmv_threshold = Column(Numeric(12, 2), nullable=True)  # GMV required for this badge
    
    # Timestamps
    earned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    creator = relationship("User", back_populates="badges")
    
    def __repr__(self):
        return f"<CreatorBadge(id={self.id}, creator_id={self.creator_id}, badge_type={self.badge_type})>"