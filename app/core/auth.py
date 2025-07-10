# app/core/auth.py
"""
Authentication module using unified security service
Provides user authentication and authorization dependencies
"""

from typing import Optional, Annotated, List
from datetime import datetime, timezone
from uuid import UUID

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.core.security import (
    security_service,
    TokenExpiredException,
    InvalidTokenException,
    TokenType
)
from app.core.config import settings
from app.core.exceptions import (
    UnauthorizedException,
    ForbiddenException,
    InvalidTokenException as CustomInvalidTokenException
)
from app.models.user import User, UserRole
from app.utils.logging import get_logger

logger = get_logger(__name__)


# Custom HTTPBearer for better error messages
class CustomHTTPBearer(HTTPBearer):
    """Enhanced HTTP Bearer with better error handling"""
    
    async def __call__(self, request: Request) -> Optional[HTTPAuthorizationCredentials]:
        try:
            credentials = await super().__call__(request)
            if not credentials:
                return None
            return credentials
        except HTTPException:
            raise UnauthorizedException(
                detail="Invalid authentication credentials"
            )


# Security scheme instance
security = CustomHTTPBearer(auto_error=False)


async def check_token_blacklist(
    token: str,
    db: AsyncSession
) -> bool:
    """
    Check if token is blacklisted
    For now, this is a placeholder - implement with Redis or database table later
    """
    if not settings.ENABLE_TOKEN_BLACKLIST:
        return False
    
    # TODO: Implement token blacklist check
    # Option 1: Create a blacklisted_tokens table in database
    # Option 2: Add Redis support later
    return False


async def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> User:
    """
    Get current user from JWT token with enhanced security
    """
    if not credentials:
        raise UnauthorizedException(detail="Not authenticated")
    
    token = credentials.credentials
    
    try:
        # Check blacklist first (placeholder for now)
        if await check_token_blacklist(token, db):
            raise InvalidTokenException("Token has been revoked")
        
        # Decode token using unified security service
        token_data = security_service.decode_access_token(token)
        
        # Extract user identification
        user_id = token_data.sub
        email = token_data.metadata.get("email")
        
        if not user_id:
            raise InvalidTokenException("Invalid token payload")
        
    except TokenExpiredException:
        raise UnauthorizedException(detail="Token has expired")
    except InvalidTokenException as e:
        raise UnauthorizedException(detail=str(e))
    except Exception as e:
        logger.error(f"Token decode error: {e}")
        raise UnauthorizedException(detail="Could not validate credentials")
    
    # Build query
    try:
        query = select(User).where(User.is_active == True)
        
        # Try UUID first
        try:
            user_uuid = UUID(user_id)
            query = query.where(User.id == user_uuid)
        except ValueError:
            # Not a UUID, try email
            if email:
                query = query.where(User.email == email)
            else:
                query = query.where(User.username == user_id)
        
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
    except Exception as e:
        logger.error(f"Database error fetching user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error"
        )
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update last login (not last_seen)
    try:
        user.last_login = datetime.now(timezone.utc)
        await db.commit()
    except Exception as e:
        logger.warning(f"Failed to update last_login: {e}")
        # Don't fail the request for this
    
    # Store user in request state for rate limiting (if request is available)
    # This is used by the rate limiter
    # Note: credentials._request might not always be available
    
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Get current active user with validation"""
    if not current_user.is_active:
        raise ForbiddenException(detail="Inactive user account")
    
    # Check if user is banned
    if hasattr(current_user, 'is_banned') and current_user.is_banned:
        raise ForbiddenException(detail="User account has been banned")
    
    return current_user


async def get_current_verified_user(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> User:
    """Get current user with verified email"""
    if not current_user.email_verified:
        raise ForbiddenException(
            detail="Email verification required. Please check your email."
        )
    
    return current_user


async def get_optional_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> Optional[User]:
    """Get user if authenticated, None otherwise"""
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except (HTTPException, UnauthorizedException, ForbiddenException):
        return None


class RoleChecker:
    """
    Dependency class to check user roles with caching
    
    Usage:
        @router.get("/admin", dependencies=[Depends(RoleChecker(["admin"]))])
    """
    
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = [role.upper() for role in allowed_roles]
    
    async def __call__(
        self,
        current_user: Annotated[User, Depends(get_current_active_user)]
    ) -> User:
        user_role = current_user.role.upper() if isinstance(current_user.role, str) else current_user.role.value
        
        if user_role not in self.allowed_roles:
            logger.warning(
                f"Access denied for user {current_user.id} with role {user_role}. "
                f"Required roles: {self.allowed_roles}"
            )
            raise ForbiddenException(
                detail=f"Insufficient permissions. Required role: {', '.join(self.allowed_roles)}"
            )
        
        return current_user


class PermissionChecker:
    """
    Dependency class to check specific permissions
    
    Usage:
        @router.post("/campaigns", dependencies=[Depends(PermissionChecker("campaigns", "write"))])
    """
    
    def __init__(self, resource: str, action: str):
        self.resource = resource
        self.action = action
    
    async def __call__(
        self,
        current_user: Annotated[User, Depends(get_current_active_user)]
    ) -> User:
        user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
        
        if not security_service.has_permission(user_role, self.resource, self.action):
            logger.warning(
                f"Permission denied for user {current_user.id} ({user_role}) "
                f"on {self.resource}:{self.action}"
            )
            raise ForbiddenException(
                detail=f"Permission denied: {self.resource}:{self.action}"
            )
        
        return current_user


class ScopeChecker:
    """
    Dependency to check token scopes
    
    Usage:
        @router.get("/api/data", dependencies=[Depends(ScopeChecker(["api:read"]))])
    """
    
    def __init__(self, required_scopes: List[str]):
        self.required_scopes = required_scopes
    
    async def __call__(
        self,
        credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
    ) -> bool:
        if not credentials:
            raise UnauthorizedException(detail="Not authenticated")
        
        try:
            # Decode token
            token_data = security_service.decode_access_token(credentials.credentials)
            
            # Check scopes
            if not security_service.check_scopes(self.required_scopes, token_data.scopes):
                missing_scopes = set(self.required_scopes) - set(token_data.scopes)
                raise ForbiddenException(
                    detail=f"Missing required scopes: {', '.join(missing_scopes)}"
                )
            
            return True
            
        except TokenExpiredException:
            raise UnauthorizedException(detail="Token has expired")
        except InvalidTokenException as e:
            raise UnauthorizedException(detail=str(e))


# Convenience role checkers
# To functions that return instances:
def require_admin():
    return RoleChecker(["admin"])

def require_agency():
    return RoleChecker(["agency", "admin"])

def require_creator():
    return RoleChecker(["creator"])

def require_brand():
    return RoleChecker(["brand", "admin"])

# Permission helpers
def require_permission(resource: str, action: str):
    """Require specific permission"""
    return PermissionChecker(resource, action)

def require_scopes(scopes: List[str]):
    """Require specific token scopes"""
    return ScopeChecker(scopes)

# Backward compatibility aliases
def require_admin_role():
    return require_admin()

def require_agency_role():
    return require_agency()

def require_creator_role():
    return require_creator()

def require_brand_role():
    return require_brand()

# For endpoints that need the user or None
GetOptionalUser = Annotated[Optional[User], Depends(get_optional_user)]
GetCurrentUser = Annotated[User, Depends(get_current_user)]
GetCurrentActiveUser = Annotated[User, Depends(get_current_active_user)]
GetCurrentVerifiedUser = Annotated[User, Depends(get_current_verified_user)]