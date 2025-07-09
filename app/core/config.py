# shared-types/app/core/config.py
"""
Application configuration using Pydantic settings
Enhanced with security improvements and microservice support
"""

from typing import Optional, List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, validator
import json
import secrets
import logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings with validation"""
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # Application
    APP_NAME: str = "TikTok Shop Creator CRM"
    APP_VERSION: str = "1.0.0"
    VERSION: str = "1.0.0"  # Alias for compatibility
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # API
    API_V1_STR: str = "/api/v1"
    API_V1_PREFIX: str = "/api/v1"  # Alias for compatibility
    
    # Security Configuration
    SECRET_KEY: str = Field(
        default="super-secret-key-for-development-change-in-production-minimum-32-chars",
        description="Application secret key - MUST be changed in production"
    )
    
    # JWT Configuration - Enhanced with separate refresh secret
    JWT_SECRET_KEY: str = Field(
        default="jwt-secret-key-for-development-change-in-production-minimum-32-chars",
        description="JWT access token secret - MUST be changed in production"
    )
    JWT_REFRESH_SECRET_KEY: Optional[str] = Field(
        default=None,
        description="JWT refresh token secret - auto-generated if not provided"
    )
    
    # JWT Settings
    ALGORITHM: str = "HS256"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Enhanced Security Settings
    MIN_PASSWORD_LENGTH: int = 8
    REQUIRE_PASSWORD_COMPLEXITY: bool = True
    PASSWORD_RESET_TOKEN_EXPIRE_HOURS: int = 1
    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24
    
    # Token Security
    ENABLE_TOKEN_BLACKLIST: bool = True
    TOKEN_BLACKLIST_CHECK_ENABLED: bool = True
    API_KEY_PREFIX: str = "tsc_"  # TikTok Shop CRM
    
    # Rate Limiting - Enhanced
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_HOUR: int = 1000
    RATE_LIMIT_PER_MINUTE: int = 100
    LOGIN_ATTEMPT_LIMIT: int = 5
    LOGIN_ATTEMPT_WINDOW_MINUTES: int = 15
    PASSWORD_RESET_LIMIT_PER_HOUR: int = 3
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:admin@localhost:5432/crm_campaigns_db"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40
    
    # Redis - Enhanced with multiple databases
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_DEFAULT_DB: int = 0
    REDIS_CACHE_DB: int = 0
    REDIS_TOKEN_BLACKLIST_DB: int = 1
    REDIS_RATE_LIMIT_DB: int = 2
    REDIS_SESSION_DB: int = 3
    REDIS_CELERY_BROKER_DB: int = 4
    REDIS_CELERY_RESULT_DB: int = 5
    
    # Service Discovery (for microservices)
    SERVICE_DISCOVERY_ENABLED: bool = False
    USER_SERVICE_URL: str = Field(default="http://user-service:8000")
    CAMPAIGN_SERVICE_URL: str = Field(default="http://campaign-service:8000")
    PAYMENT_SERVICE_URL: str = Field(default="http://payment-service:8000")
    NOTIFICATION_SERVICE_URL: str = Field(default="http://notification-service:8000")
    ANALYTICS_SERVICE_URL: str = Field(default="http://analytics-service:8000")
    
    # Service Authentication
    SERVICE_AUTH_ENABLED: bool = True
    SERVICE_AUTH_TOKEN: Optional[str] = Field(default=None)
    
    # CORS
    BACKEND_CORS_ORIGINS: Union[List[str], str] = ["http://localhost:3000", "http://localhost:8006"]
    
    @property
    def cors_origins(self) -> List[str]:
        """Parse CORS origins from environment"""
        if isinstance(self.BACKEND_CORS_ORIGINS, str):
            try:
                return json.loads(self.BACKEND_CORS_ORIGINS)
            except json.JSONDecodeError:
                return [origin.strip() for origin in self.BACKEND_CORS_ORIGINS.split(",")]
        return self.BACKEND_CORS_ORIGINS
    
    # AWS (Optional)
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: Optional[str] = None
    
    # SendBlue SMS
    SENDBLUE_API_KEY: Optional[str] = None
    SENDBLUE_API_URL: str = "https://api.sendblue.co/api/v1"
    
    # TikTok Shop Integration
    TIKTOK_SHOP_API_KEY: Optional[str] = None
    TIKTOK_SHOP_API_SECRET: Optional[str] = None
    TIKTOK_SHOP_APP_ID: Optional[str] = None
    TIKTOK_SHOP_SHOP_ID: Optional[str] = None
    TIKTOK_SHOP_API_URL: str = "https://open-api.tiktokglobalshop.com"
    
    # Discord Integration
    DISCORD_BOT_TOKEN: Optional[str] = None
    DISCORD_CLIENT_ID: Optional[str] = None
    DISCORD_CLIENT_SECRET: Optional[str] = None
    DISCORD_REDIRECT_URI: Optional[str] = None
    
    # OAuth Settings
    OAUTH_STATE_EXPIRE_MINUTES: int = 10
    OAUTH_CODE_EXPIRE_MINUTES: int = 10
    
    # Stripe Payment
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    
    # Fanbasis Payment (Alternative)
    FANBASIS_API_KEY: Optional[str] = None
    FANBASIS_API_URL: Optional[str] = None
    FANBASIS_API_SECRET: Optional[str] = None
    
    # Payment Settings
    MINIMUM_PAYOUT_AMOUNT: float = 10.0
    MAXIMUM_PAYOUT_AMOUNT: float = 10000.0
    PAYOUT_PROCESSING_DAYS: List[str] = ["monday", "friday"]
    PAYMENT_RETRY_ATTEMPTS: int = 3
    
    # Email/SMTP
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    FROM_EMAIL: str = "noreply@launchpaid.com"
    
    # Monitoring
    SENTRY_DSN: Optional[str] = None
    
    # File Upload
    MAX_FILE_SIZE: int = 10485760  # 10MB
    ALLOWED_EXTENSIONS: Union[List[str], str] = [".jpg", ".jpeg", ".png", ".gif", ".mp4", ".mov"]
    
    @property
    def allowed_extensions(self) -> List[str]:
        """Parse allowed extensions from environment"""
        if isinstance(self.ALLOWED_EXTENSIONS, str):
            try:
                return json.loads(self.ALLOWED_EXTENSIONS)
            except json.JSONDecodeError:
                return [ext.strip() for ext in self.ALLOWED_EXTENSIONS.split(",")]
        return self.ALLOWED_EXTENSIONS
    
    # Celery/Background Tasks
    CELERY_BROKER_URL: str = "redis://localhost:6379/4"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/5"
    
    # Creator specific settings
    CREATOR_PROFILE_CACHE_TTL: int = 600
    CREATOR_BADGE_CACHE_TTL: int = 3600
    CREATOR_MAX_PROFILE_UPDATES_PER_HOUR: int = 20
    CREATOR_ONBOARDING_REWARD_ENABLED: bool = True
    USER_ONBOARDING_ENABLED: bool = True  # Alias
    USER_PROFILE_CACHE_TTL: int = 600  # Alias
    MAX_PROFILE_UPDATES_PER_HOUR: int = 20  # Alias
    
    # Badge System Settings
    BADGE_CHECK_INTERVAL_HOURS: int = 24
    BADGE_SYNC_BATCH_SIZE: int = 100
    BADGE_PROGRESS_CACHE_TTL: int = 300
    BADGE_LEADERBOARD_CACHE_TTL: int = 1800
    BADGE_GMV_SYNC_ENABLED: bool = True
    BADGE_NOTIFICATION_ENABLED: bool = True
    
    # GMV Sync Settings
    GMV_SYNC_INTERVAL_HOURS: int = 1
    GMV_FULL_SYNC_INTERVAL_DAYS: int = 1
    GMV_MOCK_MODE: bool = False
    
    # Demographics Settings
    DEMOGRAPHICS_SYNC_ENABLED: bool = False
    DEMOGRAPHICS_SYNC_INTERVAL_HOURS: int = 24
    DEMOGRAPHICS_SYNC_BATCH_SIZE: int = 50
    DEMOGRAPHICS_MOCK_MODE: bool = True
    DEMOGRAPHICS_CACHE_TTL: int = 300
    DEMOGRAPHICS_IMPORT_MAX_ROWS: int = 1000
    DEMOGRAPHICS_PERCENTAGE_TOLERANCE: float = 0.5
    
    # Demographics Import Settings
    DEMOGRAPHICS_ALLOWED_FORMATS: List[str] = [".csv", ".xlsx", ".xls"]
    DEMOGRAPHICS_TEMPLATE_CACHE_TTL: int = 3600
    
    # Campaign Service Settings
    MAX_CAMPAIGNS_PER_AGENCY: int = 100
    MAX_CREATORS_PER_CAMPAIGN: int = 1000
    CAMPAIGN_CACHE_TTL: int = 300
    
    # Session Management
    SESSION_EXPIRE_MINUTES: int = 60
    SESSION_EXTEND_ON_ACTIVITY: bool = True
    MAX_SESSIONS_PER_USER: int = 5
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow"
    )
    
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """Alias for SQLAlchemy compatibility"""
        return self.DATABASE_URL
    
    @validator("JWT_REFRESH_SECRET_KEY", pre=True, always=True)
    def generate_refresh_secret(cls, v, values):
        """Generate refresh secret if not provided"""
        if v is None:
            # Generate a different secret from JWT_SECRET_KEY
            base_secret = values.get("JWT_SECRET_KEY", "")
            if base_secret == "jwt-secret-key-for-development-change-in-production-minimum-32-chars":
                # Development mode - generate a predictable but different secret
                return base_secret + "-refresh"
            else:
                # Production mode - generate a secure random secret
                return secrets.token_urlsafe(32)
        return v
    
    @validator("JWT_REFRESH_SECRET_KEY")
    def ensure_different_refresh_secret(cls, v, values):
        """Ensure refresh secret is different from access secret"""
        jwt_secret = values.get("JWT_SECRET_KEY")
        if v == jwt_secret:
            logger.warning("JWT_REFRESH_SECRET_KEY is same as JWT_SECRET_KEY, generating new one")
            return secrets.token_urlsafe(32)
        return v
    
    @validator("SERVICE_AUTH_TOKEN", pre=True, always=True)
    def generate_service_token(cls, v, values):
        """Generate service auth token if not provided"""
        if v is None and values.get("SERVICE_AUTH_ENABLED", True):
            return f"service_{secrets.token_urlsafe(32)}"
        return v
    
    def get_redis_url(self, db: int = 0) -> str:
        """Get Redis URL with specific database"""
        base_url = self.REDIS_URL.rsplit("/", 1)[0]
        return f"{base_url}/{db}"
    
    @property
    def celery_broker_url(self) -> str:
        """Get Celery broker URL with correct database"""
        return self.get_redis_url(self.REDIS_CELERY_BROKER_DB)
    
    @property
    def celery_result_backend(self) -> str:
        """Get Celery result backend URL with correct database"""
        return self.get_redis_url(self.REDIS_CELERY_RESULT_DB)


# Create settings instance
settings = Settings()


# Service-specific settings extensions
class UserServiceSettings(Settings):
    """Extended settings for user service"""
    
    # Service port
    SERVICE_PORT: int = 8001
    SERVICE_NAME: str = "user-service"
    
    # User Service Specific
    MAX_LOGIN_HISTORY: int = 100
    TRACK_LOGIN_LOCATION: bool = True
    
    # Phone verification
    PHONE_VERIFICATION_ENABLED: bool = True
    PHONE_VERIFICATION_CODE_LENGTH: int = 6
    PHONE_VERIFICATION_EXPIRE_MINUTES: int = 10
    
    # Profile completion rewards
    PROFILE_COMPLETION_BONUS_ENABLED: bool = True
    PROFILE_COMPLETION_BONUS_AMOUNT: float = 10.0


class CampaignServiceSettings(Settings):
    """Extended settings for campaign service"""
    
    # Service port
    SERVICE_PORT: int = 8002
    SERVICE_NAME: str = "campaign-service"
    
    # Campaign specific
    CAMPAIGN_APPROVAL_REQUIRED: bool = True
    CAMPAIGN_AUTO_CLOSE_DAYS: int = 90
    CAMPAIGN_EXTENSION_MAX_DAYS: int = 30
    
    # Application process
    APPLICATION_REVIEW_TIMEOUT_HOURS: int = 72
    APPLICATION_AUTO_APPROVE: bool = False
    MAX_PENDING_APPLICATIONS_PER_CREATOR: int = 10


class PaymentServiceSettings(Settings):
    """Extended settings for payment service"""
    
    # Service port
    SERVICE_PORT: int = 8003
    SERVICE_NAME: str = "payment-service"
    
    # Tax settings
    TAX_WITHHOLDING_ENABLED: bool = True
    DEFAULT_TAX_RATE: float = 0.0
    W9_REQUIRED: bool = True
    
    # Payout settings
    PAYOUT_APPROVAL_REQUIRED: bool = True
    PAYOUT_BATCH_SIZE: int = 100
    PAYOUT_RETRY_DELAY_HOURS: int = 24


# Factory functions
def get_user_service_settings() -> UserServiceSettings:
    """Get settings for user service"""
    return UserServiceSettings()


def get_campaign_service_settings() -> CampaignServiceSettings:
    """Get settings for campaign service"""
    return CampaignServiceSettings()


def get_payment_service_settings() -> PaymentServiceSettings:
    """Get settings for payment service"""
    return PaymentServiceSettings()