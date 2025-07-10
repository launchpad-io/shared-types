# app/core/security.py
"""
Unified Security Service for TikTok Shop CRM
Handles authentication, authorization, and cryptographic operations
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Union, Dict, Any, Tuple, List, Set
from enum import Enum
import secrets
import string
import logging
from functools import lru_cache
import re

from jose import JWTError, jwt, ExpiredSignatureError
from passlib.context import CryptContext
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Password hashing configuration
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12  # Increase rounds for better security
)


class TokenType(str, Enum):
    """Token types for different authentication flows"""
    ACCESS = "access"
    REFRESH = "refresh"
    RESET = "reset"
    VERIFICATION = "verification"
    API_KEY = "api_key"


class TokenData(BaseModel):
    """Token payload data structure"""
    sub: str  # Subject (user_id)
    type: TokenType
    exp: datetime
    iat: datetime
    jti: Optional[str] = Field(default_factory=lambda: secrets.token_urlsafe(16))
    scopes: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SecurityConfig(BaseModel):
    """Security configuration - compatible with existing Settings"""
    jwt_secret_key: str
    jwt_refresh_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    reset_token_expire_hours: int = 1
    verification_token_expire_hours: int = 24
    api_key_prefix: str = "tsc_"  # TikTok Shop CRM
    min_password_length: int = 8
    require_password_complexity: bool = True
    enable_token_blacklist: bool = True
    enable_rate_limiting: bool = True
    
    @classmethod
    def from_settings(cls, settings) -> "SecurityConfig":
        """Create SecurityConfig from existing Settings object"""
        return cls(
            jwt_secret_key=settings.JWT_SECRET_KEY,
            jwt_refresh_secret_key=getattr(settings, 'JWT_REFRESH_SECRET_KEY', settings.JWT_SECRET_KEY + '-refresh'),
            jwt_algorithm=settings.JWT_ALGORITHM,
            access_token_expire_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            refresh_token_expire_days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS,
            reset_token_expire_hours=getattr(settings, 'PASSWORD_RESET_TOKEN_EXPIRE_HOURS', 1),
            verification_token_expire_hours=getattr(settings, 'EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS', 24),
            api_key_prefix=getattr(settings, 'API_KEY_PREFIX', 'tsc_'),
            min_password_length=getattr(settings, 'MIN_PASSWORD_LENGTH', 8),
            require_password_complexity=getattr(settings, 'REQUIRE_PASSWORD_COMPLEXITY', True),
            enable_token_blacklist=getattr(settings, 'ENABLE_TOKEN_BLACKLIST', True),
            enable_rate_limiting=getattr(settings, 'RATE_LIMIT_ENABLED', True),
        )


class SecurityException(Exception):
    """Base exception for security operations"""
    pass


class TokenExpiredException(SecurityException):
    """Token has expired"""
    pass


class InvalidTokenException(SecurityException):
    """Token is invalid or malformed"""
    pass


class InvalidCredentialsException(SecurityException):
    """Invalid username or password"""
    pass


class UnauthorizedException(SecurityException):
    """User is not authorized for this action"""
    pass


class SecurityService:
    """
    Unified security service for authentication and authorization
    """
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self._token_blacklist: Set[str] = set()  # In production, use Redis
        
    # Password Operations
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            logger.error(f"Password verification error: {str(e)}")
            return False
    
    def validate_password_strength(self, password: str) -> Tuple[bool, Optional[str]]:
        """
        Validate password meets security requirements
        Returns: (is_valid, error_message)
        """
        if len(password) < self.config.min_password_length:
            return False, f"Password must be at least {self.config.min_password_length} characters"
        
        if self.config.require_password_complexity:
            checks = [
                (r"[A-Z]", "at least one uppercase letter"),
                (r"[a-z]", "at least one lowercase letter"),
                (r"\d", "at least one number"),
                (r"[!@#$%^&*(),.?\":{}|<>]", "at least one special character")
            ]
            
            for pattern, requirement in checks:
                if not re.search(pattern, password):
                    return False, f"Password must contain {requirement}"
        
        return True, None
    
    # Token Generation
    
    def create_access_token(
        self,
        subject: Union[str, int],
        scopes: Optional[List[str]] = None,
        expires_delta: Optional[timedelta] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create JWT access token with enhanced security"""
        expire = datetime.now(timezone.utc) + (
            expires_delta or timedelta(minutes=self.config.access_token_expire_minutes)
        )
        
        token_data = TokenData(
            sub=str(subject),
            type=TokenType.ACCESS,
            exp=expire,
            iat=datetime.now(timezone.utc),
            scopes=scopes or [],
            metadata=metadata or {}
        )
        
        payload = token_data.model_dump(mode="json")
        return jwt.encode(payload, self.config.jwt_secret_key, algorithm=self.config.jwt_algorithm)
    
    def create_refresh_token(
        self,
        subject: Union[str, int],
        device_info: Optional[Dict[str, Any]] = None,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT refresh token"""
        expire = datetime.now(timezone.utc) + (
            expires_delta or timedelta(days=self.config.refresh_token_expire_days)
        )
        
        token_data = TokenData(
            sub=str(subject),
            type=TokenType.REFRESH,
            exp=expire,
            iat=datetime.now(timezone.utc),
            metadata={"device": device_info} if device_info else {}
        )
        
        payload = token_data.model_dump(mode="json")
        return jwt.encode(
            payload,
            self.config.jwt_refresh_secret_key,
            algorithm=self.config.jwt_algorithm
        )
    
    def create_token_pair(
        self,
        subject: Union[str, int],
        scopes: Optional[List[str]] = None,
        device_info: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str]:
        """Create both access and refresh tokens"""
        access_token = self.create_access_token(subject, scopes=scopes)
        refresh_token = self.create_refresh_token(subject, device_info=device_info)
        return access_token, refresh_token
    
    # Token Validation
    
    def decode_token(self, token: str, expected_type: TokenType) -> TokenData:
        """
        Decode and validate JWT token
        
        Raises:
            TokenExpiredException: If token is expired
            InvalidTokenException: If token is invalid
        """
        try:
            # Check if token is blacklisted
            if self.config.enable_token_blacklist and self._is_token_blacklisted(token):
                raise InvalidTokenException("Token has been revoked")
            
            # Select appropriate secret based on token type
            secret = (
                self.config.jwt_refresh_secret_key 
                if expected_type == TokenType.REFRESH 
                else self.config.jwt_secret_key
            )
            
            payload = jwt.decode(
                token,
                secret,
                algorithms=[self.config.jwt_algorithm]
            )
            
            token_data = TokenData(**payload)
            
            # Verify token type
            if token_data.type != expected_type:
                raise InvalidTokenException(f"Expected {expected_type} token, got {token_data.type}")
            
            return token_data
            
        except ExpiredSignatureError:
            raise TokenExpiredException("Token has expired")
        except JWTError as e:
            logger.debug(f"Token decode error: {str(e)}")
            raise InvalidTokenException("Invalid token")
    
    def decode_access_token(self, token: str) -> TokenData:
        """Decode access token"""
        return self.decode_token(token, TokenType.ACCESS)
    
    def decode_refresh_token(self, token: str) -> TokenData:
        """Decode refresh token"""
        return self.decode_token(token, TokenType.REFRESH)
    
    # Token Management
    
    def revoke_token(self, token: str, jti: Optional[str] = None) -> None:
        """Revoke a token by adding to blacklist"""
        if self.config.enable_token_blacklist:
            # In production, store in Redis with TTL
            self._token_blacklist.add(jti or token)
    
    def _is_token_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted"""
        # In production, check Redis
        return token in self._token_blacklist
    
    # Utility Functions
    
    def generate_token(self, length: int = 32) -> str:
        """Generate a secure random token"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def generate_api_key(self) -> str:
        """Generate an API key with prefix"""
        return f"{self.config.api_key_prefix}{self.generate_token(32)}"
    
    def generate_verification_token(self) -> Tuple[str, datetime]:
        """Generate email verification token"""
        token = self.generate_token(32)
        expires = datetime.now(timezone.utc) + timedelta(
            hours=self.config.verification_token_expire_hours
        )
        return token, expires
    
    def generate_reset_token(self) -> Tuple[str, datetime]:
        """Generate password reset token"""
        token = self.generate_token(32)
        expires = datetime.now(timezone.utc) + timedelta(
            hours=self.config.reset_token_expire_hours
        )
        return token, expires
    
    def extract_token_from_header(self, authorization: str) -> Optional[str]:
        """Extract token from Authorization header"""
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
        return None
    
    # Authorization
    
    def check_scopes(self, required_scopes: List[str], token_scopes: List[str]) -> bool:
        """Check if token has required scopes"""
        return all(scope in token_scopes for scope in required_scopes)
    
    def has_permission(
        self,
        user_role: str,
        resource: str,
        action: str,
        custom_permissions: Optional[Dict[str, List[str]]] = None
    ) -> bool:
        """
        Check if user role has permission for resource and action
        
        Args:
            user_role: User's role
            resource: Resource name (e.g., 'profile', 'campaign')
            action: Action name (e.g., 'read', 'write', 'delete')
            custom_permissions: Optional custom permission mapping
        """
        # Default permissions for TikTok Shop CRM
        default_permissions = {
            "ADMIN": ["*"],  # Admin has all permissions
            "CREATOR": [
                "profile:*",
                "badges:read",
                "demographics:*",
                "campaigns:read",
                "deliverables:*",
                "payments:read"
            ],
            "AGENCY": [
                "campaigns:*",
                "creators:read",
                "analytics:*",
                "profile:*",
                "payments:*"
            ],
            "BRAND": [
                "campaigns:read",
                "creators:read",
                "analytics:read",
                "profile:*"
            ]
        }
        
        permissions = custom_permissions or default_permissions
        user_permissions = permissions.get(user_role, [])
        permission_string = f"{resource}:{action}"
        
        # Check for wildcard permissions
        if "*" in user_permissions:
            return True
        
        # Check for resource wildcard
        if f"{resource}:*" in user_permissions:
            return True
        
        # Check for exact permission
        return permission_string in user_permissions


# Factory function to create security service
@lru_cache()
def get_security_service() -> SecurityService:
    """
    Get cached security service instance
    Compatible with existing settings structure
    """
    from app.core.config import settings
    
    config = SecurityConfig.from_settings(settings)
    return SecurityService(config)


# Create a default instance using existing settings
try:
    from app.core.config import settings
    _default_config = SecurityConfig.from_settings(settings)
    security_service = SecurityService(_default_config)
except ImportError:
    # Fallback for testing or when settings not available
    _default_config = SecurityConfig(
        jwt_secret_key="test-secret-key",
        jwt_refresh_secret_key="test-refresh-secret-key"
    )
    security_service = SecurityService(_default_config)

# Convenience exports
hash_password = security_service.hash_password
verify_password = security_service.verify_password
create_access_token = security_service.create_access_token
create_refresh_token = security_service.create_refresh_token
create_token_pair = security_service.create_token_pair
decode_access_token = security_service.decode_access_token
decode_refresh_token = security_service.decode_refresh_token
has_permission = security_service.has_permission

# Aliases for backward compatibility
get_password_hash = hash_password  # Some code might use this name