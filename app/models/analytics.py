from sqlalchemy import Column, String, Integer, Float, JSON, ForeignKey
from app.db.base_class import Base

class Analytics(Base):
    __tablename__ = "analytics"
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("user.id"))
    period = Column(String)
    total_views = Column(Integer)
    total_engagement = Column(Float)
    follower_growth = Column(Integer)
    gmv_growth = Column(Float)
    best_performing_content = Column(String)
    peak_posting_time = Column(String)
    audience_retention = Column(Float)
    recommendations = Column(JSON)
