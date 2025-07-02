"""
Database base configuration for TikTok Shop Creator CRM
Imports all models to ensure they're registered with SQLAlchemy
"""

# Import the base class first
from app.db.base_class import Base  # noqa

# Import all models after Base is defined
# This will be done at the end of the file to avoid circular imports

__all__ = ["Base"]