"""
Models package
"""

# Import models here to make them available at package level
from app.models.user import User, UserToken
from app.models.creator import CreatorBadge, CreatorAudienceDemographic

# If your code expects PlatformUser, create an alias
PlatformUser = User

__all__ = [
    "User",
    "UserToken",
    "PlatformUser",  # Alias for compatibility
    "CreatorBadge",
    "CreatorAudienceDemographic"
]