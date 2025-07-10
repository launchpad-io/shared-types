"""
Authentication endpoints for TikTok Shop Creator CRM
"""
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from typing import Optional

from app.db.session import get_db
from app.core.security import (
    create_token_pair, 
    verify_password, 
    hash_password,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    TokenExpiredException,
    InvalidTokenException
)
from app.core.dependencies import get_current_active_user
from app.models.user import User, UserRole
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Pydantic schemas for auth endpoints
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional

class SignupRequest(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.CREATOR
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    
    @validator('username')
    def username_alphanumeric(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username must be alphanumeric with optional underscores and hyphens')
        return v.lower()

class LoginRequest(BaseModel):
    username: str  # Can be email or username
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict
    message: Optional[str] = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class MessageResponse(BaseModel):
    message: str
    success: bool = True

# Auth endpoints
@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    request: SignupRequest,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user account"""
    try:
        # Check if user exists
        query = select(User).where(
            (User.email == request.email) | (User.username == request.username)
        )
        result = await db.execute(query)
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            if existing_user.email == request.email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this email already exists"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
        
        # Create new user
        user = User(
            email=request.email.lower(),
            username=request.username.lower(),
            hashed_password=hash_password(request.password),
            role=request.role,
            first_name=request.first_name,
            last_name=request.last_name,
            created_at=datetime.now(timezone.utc),
            is_active=True,
            email_verified=False  # Require email verification
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        # Create tokens
        access_token, refresh_token = create_token_pair(
            str(user.id),
            scopes=[user.role.value]
        )
        
        # Prepare user data for response
        user_data = {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "role": user.role.value,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_active": user.is_active,
            "email_verified": user.email_verified,
            "created_at": user.created_at.isoformat()
        }
        
        logger.info(f"New user registered: {user.username} ({user.email})")
        
        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=user_data,
            message="Registration successful. Please verify your email."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Signup error: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during registration"
        )

@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """Login with email/username and password"""
    try:
        # Find user by email or username
        query = select(User).where(
            (User.email == request.username.lower()) | 
            (User.username == request.username.lower())
        )
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Verify password
        if not verify_password(request.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive. Please contact support."
            )
        
        # Create tokens
        access_token, refresh_token = create_token_pair(
            str(user.id),
            scopes=[user.role.value]
        )
        
        # Update last login
        user.last_login = datetime.now(timezone.utc)
        await db.commit()
        
        # Prepare user data for response
        user_data = {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "role": user.role.value,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_active": user.is_active,
            "email_verified": user.email_verified,
            "last_login": user.last_login.isoformat()
        }
        
        logger.info(f"User logged in: {user.username}")
        
        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=user_data,
            message="Login successful"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login"
        )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token"""
    try:
        # Decode refresh token
        token_data = decode_refresh_token(request.refresh_token)
        user_id = token_data.sub
        
        # Get user
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Create new token pair
        access_token, refresh_token = create_token_pair(
            str(user.id),
            scopes=[user.role.value]
        )
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        )
        
    except (TokenExpiredException, InvalidTokenException):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during token refresh"
        )

@router.get("/me")
async def get_current_user(
    current_user: User = Depends(get_current_active_user)
):
    """Get current authenticated user info"""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "username": current_user.username,
        "role": current_user.role.value,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "is_active": current_user.is_active,
        "email_verified": current_user.email_verified,
        "profile_completion_percentage": current_user.profile_completion_percentage,
        "created_at": current_user.created_at.isoformat(),
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None
    }

@router.post("/logout", response_model=MessageResponse)
async def logout(
    current_user: User = Depends(get_current_active_user)
):
    """Logout current user (client should discard tokens)"""
    # In a production app, you might want to blacklist the token here
    logger.info(f"User logged out: {current_user.username}")
    
    return MessageResponse(
        message="Logged out successfully",
        success=True
    )

@router.get("/health")
async def health_check():
    """Health check for auth service"""
    return {
        "status": "healthy",
        "service": "auth",
        "endpoints": [
            "/signup",
            "/login",
            "/refresh",
            "/me",
            "/logout"
        ]
    }