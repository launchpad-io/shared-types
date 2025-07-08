from typing import Optional, Annotated
from datetime import datetime
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.core.security import security_service
from app.models.user import User  # Changed from PlatformUser to User
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Custom HTTPBearer for better error messages
class CustomHTTPBearer(HTTPBearer):
    async def __call__(self, request: Request) -> Optional[HTTPAuthorizationCredentials]:
        try:
            return await super().__call__(request)
        except HTTPException:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

security = CustomHTTPBearer(auto_error=False)

async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> User:
    """
    Get current user from JWT token
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Decode token
        payload = await security_service.decode_token(credentials.credentials)
        email: str = payload.get("sub")
        user_id: str = payload.get("user_id")
        
        if email is None and user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )
    except Exception as e:
        logger.error(f"Token decode error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    
    # Build query based on available data
    query = select(User).where(User.is_active == True)
    
    if user_id:
        query = query.where(User.id == user_id)
    elif email:
        query = query.where(User.email == email)
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    
    # Get user from database
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    await db.commit()
    
    return user

async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Get current active user
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    
    return current_user

async def get_current_verified_user(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> User:
    """
    Get current verified user
    """
    if not current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified",
        )
    
    return current_user

class RoleChecker:
    """
    Dependency to check user roles
    
    Usage:
        @router.get("/admin", dependencies=[Depends(RoleChecker(["admin"]))])
    """
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles
    
    async def __call__(
        self,
        current_user: Annotated[User, Depends(get_current_active_user)]
    ) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {', '.join(self.allowed_roles)}",
            )
        return current_user

# Convenience dependencies
require_admin = Depends(RoleChecker(["admin"]))
require_agency = Depends(RoleChecker(["agency", "admin"]))
require_creator = Depends(RoleChecker(["creator"]))
require_brand = Depends(RoleChecker(["brand", "admin"]))

# Optional user (for endpoints that work with or without auth)
async def get_optional_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> Optional[User]:
    """
    Get user if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None

# Alias for backward compatibility if needed
PlatformUser = User