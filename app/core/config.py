"""
Application configuration using Pydantic settings
"""

from typing import Optional, List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
import json


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
    
    # Security
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    JWT_SECRET_KEY: str = "your-jwt-secret-key"
    ALGORITHM: str = "HS256"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost/crm_db"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # CORS
    BACKEND_CORS_ORIGINS: Union[List[str], str] = ["http://localhost:3000", "http://localhost:8000"]
    
    @property
    def cors_origins(self) -> List[str]:
        """Parse CORS origins from environment"""
        if isinstance(self.BACKEND_CORS_ORIGINS, str):
            try:
                return json.loads(self.BACKEND_CORS_ORIGINS)
            except json.JSONDecodeError:
                return [origin.strip() for origin in self.BACKEND_CORS_ORIGINS.split(",")]
        return self.BACKEND_CORS_ORIGINS
    
    # Rate Limiting
    RATE_LIMIT_PER_HOUR: int = 1000
    RATE_LIMIT_PER_MINUTE: int = 100
    
    # AWS (Optional)
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: Optional[str] = None
    
    # SendBlue SMS
    SENDBLUE_API_KEY: Optional[str] = None
    SENDBLUE_API_URL: str = "https://api.sendblue.co/api/v1"
    
    # External APIs
    TIKTOK_API_KEY: Optional[str] = None
    TIKTOK_API_SECRET: Optional[str] = None
    DISCORD_BOT_TOKEN: Optional[str] = None
    
    # Stripe
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    
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
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    # Creator specific settings
    CREATOR_PROFILE_CACHE_TTL: int = 600
    CREATOR_BADGE_CACHE_TTL: int = 3600
    CREATOR_MAX_PROFILE_UPDATES_PER_HOUR: int = 20
    CREATOR_ONBOARDING_REWARD_ENABLED: bool = True
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        # Allow extra fields from .env that aren't defined here
        extra="allow"
    )
    
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """Alias for SQLAlchemy compatibility"""
        return self.DATABASE_URL


# Create settings instance
settings = Settings()