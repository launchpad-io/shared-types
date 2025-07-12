from sqlalchemy import Column, String, DECIMAL, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from app.db.base_class import Base

class CreatorAudienceDemographics(Base):
    """
    Model for creator audience demographics data
    Tracks age groups, gender, and geographical distribution of creator audiences
    """
    __tablename__ = "creator_audience_demographics"
    __table_args__ = {'schema': 'users', 'extend_existing': True}

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.uuid_generate_v4()
    )
    
    creator_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.users.id', ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    age_group = Column(
        String(20),
        nullable=False,
        index=True,
        comment="Age group: 13-17, 18-24, 25-34, 35-44, 45-54, 55+"
    )
    
    gender = Column(
        String,
        nullable=False,
        default="not_specified",
        comment="Gender: male, female, other, not_specified"
    )
    
    percentage = Column(
        DECIMAL(5, 2),
        nullable=False,
        comment="Percentage of audience in this demographic segment"
    )
    
    country = Column(
        String(100),
        nullable=True,
        index=True
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationships (uncomment when User model is available)
    # creator = relationship("User", back_populates="audience_demographics")

    def __repr__(self):
        return f"<CreatorAudienceDemographics(creator_id={self.creator_id}, age={self.age_group}, gender={self.gender}, pct={self.percentage}%)>"

    @property
    def segment_key(self):
        """Returns a unique key for this demographic segment"""
        return f"{self.age_group}_{self.gender}_{self.country or 'ALL'}"

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': str(self.id),
            'creator_id': str(self.creator_id),
            'age_group': self.age_group,
            'gender': self.gender,
            'percentage': float(self.percentage),
            'country': self.country,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
