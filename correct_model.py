from sqlalchemy import Column, String, DECIMAL, DateTime, ForeignKey
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
        doc="Unique identifier for the demographic entry"
    )
    
    creator_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.users.id', ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Reference to the creator user"
    )
    
    age_group = Column(
        String,
        nullable=False,
        doc="Age group (e.g., '18-24', '25-34')"
    )
    
    gender = Column(
        String,
        nullable=False,
        default="not_specified",
        doc="Gender (male, female, other, not_specified)"
    )
    
    percentage = Column(
        DECIMAL(5, 2),
        nullable=False,
        doc="Percentage of audience in this demographic"
    )
    
    country = Column(
        String(3),
        nullable=True,
        doc="ISO 3-letter country code"
    )
    
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        doc="Last update timestamp"
    )
    
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        doc="Creation timestamp"
    )

    def __repr__(self):
        return f"<CreatorAudienceDemographics(creator_id={self.creator_id}, age_group={self.age_group}, gender={self.gender}, percentage={self.percentage})>"
