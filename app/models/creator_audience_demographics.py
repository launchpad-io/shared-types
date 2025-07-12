# models/creator_audience_demographics.py
from sqlalchemy import Column, String, ForeignKey, DECIMAL, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
import uuid

Base = declarative_base()

# Define the gender enum to match your database type
# class GenderType(str, enum.Enum):
#     MALE = "MALE"
#     FEMALE = "FEMALE"
#     OTHER = "OTHER"
#     PREFER_NOT_TO_SAY = "PREFER_NOT_TO_SAY"

class CreatorAudienceDemographics(Base):
    __tablename__ = "creator_audience_demographics"
    __table_args__ = {'schema': 'users'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    creator_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('users.users.id', ondelete="CASCADE"),
        nullable=False
    )
    age_group = Column(String(20), nullable=False)  # '13-17', '18-24', '25-34', '35-44', '45-54', '55+'
    # gender = Column(
    #     Enum(GenderType, name='gender_type', schema='users'),
    #     nullable=False
    # )
    percentage = Column(DECIMAL(5, 2), nullable=False)  # 0.00 to 999.99
    country = Column(String(100), nullable=True)
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Optional: Add relationship to users table if you have a User model
    # creator = relationship("User", back_populates="audience_demographics")
    
    def __repr__(self):
        return f"<CreatorAudienceDemographics(creator_id={self.creator_id}, age_group={self.age_group}, percentage={self.percentage}%)>"