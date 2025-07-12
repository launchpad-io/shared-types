from sqlalchemy import Column, String, Float, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base_class import Base
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID




class GMVHistory(Base):
    __tablename__ = "gmv_history"
    id = Column(String, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.users.id"))
    period = Column(String, index=True)
    amount = Column(Float)
    date = Column(Date)
    description = Column(String, nullable=True)
    user = relationship("User")
