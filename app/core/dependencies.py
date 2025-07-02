"""
Core dependencies for FastAPI
Handles authentication, database sessions, and common dependencies
"""

from typing import Optional, Generator, List
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.core.config import settings
from app.models.user import User, UserRole
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current user from JWT token.
    
    Args:
        credentials: Bearer token from request
        db: Database session
        
    Returns:
        Current user object
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials
    
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    result = await db.execute(
        select(User).where(User.id == UUID(user_id))
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user.
    
    Args:
        current_user: User from token
        
    Returns:
        Active user object
        
    Raises:
        HTTPException: If user is not active
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


async def get_current_verified_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Get current verified user.
    
    Args:
        current_user: Current active user
        
    Returns:
        Verified user object
        
    Raises:
        HTTPException: If user email is not verified
    """
    if not current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified",
        )
    return current_user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get user if authenticated, None otherwise.
    
    Args:
        credentials: Optional bearer token
        db: Database session
        
    Returns:
        User object or None
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


async def require_creator_role(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Require user to have creator role.
    
    Args:
        current_user: Current active user
        
    Returns:
        User with creator role
        
    Raises:
        HTTPException: If user is not a creator
    """
    if current_user.role != UserRole.CREATOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Creator access required"
        )
    return current_user


async def require_admin_role(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Require user to have admin role.
    
    Args:
        current_user: Current active user
        
    Returns:
        User with admin role
        
    Raises:
        HTTPException: If user is not an admin
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def require_agency_role(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Require user to have agency role.
    
    Args:
        current_user: Current active user
        
    Returns:
        User with agency role
        
    Raises:
        HTTPException: If user is not an agency
    """
    if current_user.role != UserRole.AGENCY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agency access required"
        )
    return current_user


async def require_brand_role(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Require user to have brand role.
    
    Args:
        current_user: Current active user
        
    Returns:
        User with brand role
        
    Raises:
        HTTPException: If user is not a brand
    """
    if current_user.role != UserRole.BRAND:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Brand access required"
        )
    return current_user


class RoleChecker:
    """
    Dependency class to check user roles.
    
    Usage:
        @router.get("/admin", dependencies=[Depends(RoleChecker(["admin"]))])
    """
    
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles
    
    async def __call__(
        self,
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {', '.join(self.allowed_roles)}",
            )
        return current_user


def has_permission(user: User, resource: str, action: str) -> bool:
    """
    Check if user has permission for resource and action.
    
    Args:
        user: User to check
        resource: Resource name
        action: Action name (read, write, delete)
        
    Returns:
        True if user has permission
    """
    # Implement role-based permissions
    permissions = {
        UserRole.ADMIN: ["*"],  # Admin has all permissions
        UserRole.CREATOR: [
            "profile:read", "profile:write",
            "badges:read", "demographics:read", "demographics:write",
            "campaigns:read", "deliverables:write"
        ],
        UserRole.AGENCY: [
            "campaigns:*", "creators:read", "analytics:read",
            "profile:read", "profile:write"
        ],
        UserRole.BRAND: [
            "campaigns:read", "creators:read", "analytics:read",
            "profile:read", "profile:write"
        ]
    }
    
    user_permissions = permissions.get(user.role, [])
    permission_string = f"{resource}:{action}"
    
    # Check for wildcard permissions
    if "*" in user_permissions:
        return True
    
    # Check for resource wildcard (e.g., "campaigns:*")
    resource_wildcard = f"{resource}:*"
    if resource_wildcard in user_permissions:
        return True
    
    # Check for exact permission
    return permission_string in user_permissions


# Convenience dependencies using RoleChecker
require_admin = Depends(RoleChecker(["admin"]))
require_agency = Depends(RoleChecker(["agency", "admin"]))
require_creator = Depends(RoleChecker(["creator"]))
require_brand = Depends(RoleChecker(["brand", "admin"]))


# Export all dependencies
__all__ = [
    "get_current_user",
    "get_current_active_user",
    "get_current_verified_user",
    "get_optional_user",
    "require_creator_role",
    "require_admin_role",
    "require_agency_role",
    "require_brand_role",
    "RoleChecker",
    "has_permission",
    "require_admin",
    "require_agency",
    "require_creator",
    "require_brand",
    "get_db",
    "security"
]