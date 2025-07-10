"""
Import all models for Alembic migrations
This file should be imported by alembic/env.py to ensure all models are registered
"""

# Import base first
from app.db.base_class import Base  # noqa

# Import all models
from app.models.user import User, UserToken  # noqa
from app.models.creator import CreatorBadge, CreatorAudienceDemographic  # noqa

# Try to import badge model if it exists separately
try:
    from app.models.creator import CreatorBadge as Badge  # noqa
except ImportError:
    pass  # Badge model might not exist as a separate file

# Future models (when implemented)
# from app.models.campaign import Campaign, CampaignCreator  # noqa
# from app.models.application import Application  # noqa
# from app.models.deliverable import Deliverable  # noqa
# from app.models.payment import Payment, Payout  # noqa
# from app.models.notification import Notification  # noqa

# This ensures all models are registered with SQLAlchemy metadata
__all__ = ["Base"]
