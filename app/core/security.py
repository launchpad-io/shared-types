"""
Security utilities for password hashing and JWT tokens
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class SecurityService:
    """Service for handling security operations"""
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Generate password hash"""
        return pwd_context.hash(password)
    
    def create_access_token(
        self, 
        data: Dict[str, Any], 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.JWT_SECRET_KEY, 
            algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt
    
    def create_refresh_token(
        self, 
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
            )
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt
    
    async def decode_token(self, token: str) -> Dict[str, Any]:
        """Decode and verify JWT token"""
        try:
            payload = jwt.decode(
                token, 
                settings.JWT_SECRET_KEY, 
                algorithms=[settings.JWT_ALGORITHM]
            )
            return payload
        except JWTError:
            raise ValueError("Invalid token")


# Create global instance
security_service = SecurityService()

# Export commonly used functions
verify_password = security_service.verify_password
get_password_hash = security_service.get_password_hash
create_access_token = security_service.create_access_token
create_refresh_token = security_service.create_refresh_token


def has_permission(user, resource: str, action: str) -> bool:
    """
    Check if user has permission for resource and action.
    
    Args:
        user: User to check
        resource: Resource name
        action: Action name (read, write, delete)
        
    Returns:
        True if user has permission
    """
    from app.models.user import UserRole
    
    # Define role-based permissions
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