# app/models/__init__.py
"""
Models package - Fixed to avoid duplicate imports
"""

# Import models from their primary locations
from app.models.user import User, UserToken, UserRole, GenderType
from app.models.creator import CreatorBadge, CreatorAudienceDemographic, BadgeType, AgeGroup

# Don't import from badge.py if it exists - use creator.py as the single source

__all__ = [
    # User models
    "User",
    "UserToken",
    "UserRole",
    "GenderType",
    # Creator models
    "CreatorBadge",
    "CreatorAudienceDemographic",
    "BadgeType",
    "AgeGroup"
]