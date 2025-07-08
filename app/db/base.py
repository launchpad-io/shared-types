"""
Database base configuration for TikTok Shop Creator CRM
"""

# Import the base class - this should be imported by other modules
from app.db.base_class import Base  # noqa

# Don't import models here to avoid circular imports
# Models will be imported by Alembic's env.py when needed for migrations

__all__ = ["Base"]