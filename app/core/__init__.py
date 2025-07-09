# shared-types/app/core/__init__.py
"""
Core module for shared functionality across microservices
"""

# Configuration
from app.core.config import (
    settings,
    Settings,
    UserServiceSettings,
    CampaignServiceSettings,
    PaymentServiceSettings,
    get_user_service_settings,
    get_campaign_service_settings,
    get_payment_service_settings
)

# Security
from app.core.security import (
    security_service,
    SecurityService,
    SecurityConfig,
    hash_password,
    get_password_hash,  # Alias for hash_password
    verify_password,
    create_access_token,
    create_refresh_token,
    create_token_pair,
    decode_access_token,
    decode_refresh_token,
    has_permission,
    TokenType,
    TokenData,
    TokenExpiredException,
    InvalidTokenException,
    InvalidCredentialsException,
    UnauthorizedException as SecurityUnauthorizedException
)

# Authentication & Authorization
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

# Dependencies (includes all auth exports for compatibility)
from app.core.dependencies import (
    get_db,
    get_db_context,
    get_request_id,
    check_maintenance_mode,
    FeatureFlag,
    require_feature,
    check_service_health,
    APIVersion,
    PaginationParams
)

# Exceptions
from app.core.exceptions import (
    BaseCustomException,
    NotFoundException,
    UnauthorizedException,
    ForbiddenException,
    BadRequestException,
    ValidationException,
    ConflictException,
    BusinessLogicException,
    RateLimitException,
    InternalServerException,
    ServiceUnavailableException,
    InsufficientPermissionsException,
    InvalidTokenException as CustomInvalidTokenException,
    ExpiredTokenException,
    DuplicateException,
    InvalidRequestException
)

# Cache
from app.core.cache import (
    CacheManager,
    get_cache,
    cached,
    cache_key,
    TaggedCache,
    CacheBackend,
    RedisBackend,
    MemoryBackend,
    cache_key_wrapper,
    cache
)

# Rate Limiting
from app.core.limiter import (
    limiter,
    advanced_limiter,
    AdvancedRateLimiter,
    rate_limit,
    get_rate_limit_key
)

# Version
__version__ = "1.0.0"

# Define what's available when using "from app.core import *"
__all__ = [
    # Config
    "settings",
    "Settings",
    # Security
    "security_service",
    "hash_password",
    "get_password_hash",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "create_token_pair",
    "decode_access_token",
    "decode_refresh_token",
    "has_permission",
    # Auth
    "get_current_user",
    "get_current_active_user",
    "get_current_verified_user",
    "get_optional_user",
    "require_admin",
    "require_agency",
    "require_creator",
    "require_brand",
    "RoleChecker",
    "PermissionChecker",
    "ScopeChecker",
    # Dependencies
    "get_db",
    "PaginationParams",
    # Exceptions
    "NotFoundException",
    "UnauthorizedException",
    "ForbiddenException",
    "BadRequestException",
    "ValidationException",
    "ConflictException",
    "BusinessLogicException",
    "RateLimitException",
    # Cache
    "get_cache",
    "cached",
    "cache_key",
    # Rate Limiting
    "limiter",
    "rate_limit",
]