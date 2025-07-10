# app/core/dependencies.py
"""
Core dependencies for FastAPI - Unified version
Consolidates auth and database dependencies
"""

# Re-export everything from auth module for backward compatibility
from app.core.auth import (
    get_current_user,
    get_current_active_user,
    get_current_verified_user,
    get_optional_user,
    require_admin,
    require_agency,
    require_creator,
    require_brand,
    require_admin_role,
    require_agency_role,
    require_creator_role,
    require_brand_role,
    RoleChecker,
    PermissionChecker,
    ScopeChecker,
    require_permission,
    require_scopes,
    security,
    GetOptionalUser,
    GetCurrentUser,
    GetCurrentActiveUser,
    GetCurrentVerifiedUser
)

# Database dependencies
from app.db.session import get_db, get_db_context

# Additional dependencies
from typing import Optional, AsyncGenerator
from fastapi import Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def get_request_id(request: Request) -> str:
    """Get or generate request ID for tracing"""
    return request.headers.get("X-Request-ID", "")


async def check_maintenance_mode() -> None:
    """Check if application is in maintenance mode"""
    # This could check Redis or a config flag
    if getattr(settings, 'MAINTENANCE_MODE', False):
        from app.core.exceptions import ServiceUnavailableException
        raise ServiceUnavailableException(
            detail="System is under maintenance. Please try again later."
        )


class FeatureFlag:
    """Check if a feature is enabled"""
    
    def __init__(self, flag_name: str):
        self.flag_name = flag_name
    
    async def __call__(self) -> bool:
        """
        Check feature flag
        For now, this uses environment variables or config
        Later can be extended to use Redis or database
        """
        # Check in settings/environment
        flag_env_name = f"FEATURE_{self.flag_name.upper()}_ENABLED"
        is_enabled = getattr(settings, flag_env_name, False)
        
        # Could also check in database or cache here
        return bool(is_enabled)


def require_feature(flag_name: str):
    """Require a feature to be enabled"""
    async def check_feature(
        is_enabled: bool = Depends(FeatureFlag(flag_name))
    ):
        if not is_enabled:
            from app.core.exceptions import ForbiddenException
            raise ForbiddenException(
                detail=f"Feature '{flag_name}' is not enabled"
            )
    return check_feature


# Service health check dependency
async def check_service_health(
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Check health of all dependencies"""
    health = {
        "database": "unknown",
        "status": "unhealthy"
    }
    
    # Check database
    try:
        await db.execute("SELECT 1")
        health["database"] = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health["database"] = "unhealthy"
    
    # Overall status
    if health["database"] == "healthy":
        health["status"] = "healthy"
    
    return health


# API versioning dependency
class APIVersion:
    """Extract and validate API version from request"""
    
    def __init__(self, supported_versions: list = None):
        self.supported_versions = supported_versions or ["v1"]
    
    async def __call__(self, request: Request) -> str:
        """Extract API version from path or header"""
        # Try to get from path first
        path_parts = request.url.path.split("/")
        for part in path_parts:
            if part in self.supported_versions:
                return part
        
        # Try header
        version = request.headers.get("X-API-Version", "v1")
        if version not in self.supported_versions:
            from app.core.exceptions import BadRequestException
            raise BadRequestException(
                detail=f"Unsupported API version: {version}"
            )
        
        return version


# Pagination dependencies
class PaginationParams:
    """Common pagination parameters"""
    
    def __init__(
        self,
        page: int = 1,
        page_size: int = 20,
        max_page_size: int = 100
    ):
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20
        if page_size > max_page_size:
            page_size = max_page_size
        
        self.page = page
        self.page_size = page_size
        self.offset = (page - 1) * page_size
        self.limit = page_size


# Export all dependencies
__all__ = [
    # Auth dependencies
    "get_current_user",
    "get_current_active_user",
    "get_current_verified_user",
    "get_optional_user",
    "require_admin",
    "require_agency",
    "require_creator",
    "require_brand",
    "require_admin_role",
    "require_agency_role",
    "require_creator_role",
    "require_brand_role",
    "RoleChecker",
    "PermissionChecker",
    "ScopeChecker",
    "require_permission",
    "require_scopes",
    "security",
    "GetOptionalUser",
    "GetCurrentUser",
    "GetCurrentActiveUser",
    "GetCurrentVerifiedUser",
    # Database dependencies
    "get_db",
    "get_db_context",
    # Additional dependencies
    "get_request_id",
    "check_maintenance_mode",
    "FeatureFlag",
    "require_feature",
    "check_service_health",
    "APIVersion",
    "PaginationParams",
]