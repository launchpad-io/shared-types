"""
User profile API endpoints for TikTok Shop Creator CRM
Handles profile management, updates, and completion tracking for all user types.
"""
# app/api/v1/endpoints/users/router.py

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, Field, constr

from app.db.session import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User, UserRole
from app.schemas.user import (
    UserResponse,
    UserProfileUpdate,
    PersonalInfoUpdate,
    AddressUpdate,
    SocialMediaUpdate,
    CreatorDetailsUpdate,
    CompanyDetailsUpdate,
    NotificationPreferences,
    ProfileCompletionStatus,
    UserListResponse
)
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Remove duplicate prefix since it's added in api.py
router = APIRouter(
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized"},
        404: {"description": "User not found"},
        422: {"description": "Validation error"}
    }
)

# Pydantic model for phone validation
class PhoneNumberRequest(BaseModel):
    phone_number: constr(pattern=r'^\+?1?\d{9,15}$')

class VerificationCodeRequest(BaseModel):
    verification_code: str

# In app/api/v1/endpoints/users/router.py, update the get_current_user_profile endpoint:

@router.get("/me", response_model=UserResponse, summary="Get current user profile")
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """
    Get the current authenticated user's complete profile.
    
    Returns:
        UserResponse: Complete user profile with all fields
    """
    try:
        # Make sure all attributes are loaded before serialization
        # This prevents the MissingGreenlet error
        await db.refresh(current_user)
        
        # Convert to dict first to avoid lazy loading issues
        user_dict = {
            "id": current_user.id,
            "email": current_user.email,
            "username": current_user.username,
            "role": current_user.role,
            "is_active": current_user.is_active,
            "email_verified": current_user.email_verified,
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "phone": current_user.phone,
            "date_of_birth": current_user.date_of_birth,
            "gender": current_user.gender,
            "profile_image_url": current_user.profile_image_url,
            "bio": current_user.bio,
            "created_at": current_user.created_at,
            "updated_at": current_user.updated_at,
            "last_login": current_user.last_login,
            # Add other fields as needed
        }
        
        return UserResponse(**user_dict)
        
    except Exception as e:
        logger.error(f"Error fetching user profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user profile"
        )


@router.get("/profile/{user_id}", response_model=UserResponse, summary="Get user profile by ID")
async def get_user_profile(
    user_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """
    Get a specific user's profile by ID.
    
    Args:
        user_id: UUID of the user to fetch
        
    Returns:
        UserResponse: User profile data
        
    Raises:
        404: User not found
        403: Not authorized to view this profile
    """
    # Check permissions - users can view their own profile, admins can view any
    is_admin = current_user.role == UserRole.ADMIN
    if str(user_id) != str(current_user.id) and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this profile"
        )
    
    try:
        # Simplified implementation - in production, use ProfileService
        from sqlalchemy import select
        
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
            
        return UserResponse.model_validate(user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user profile {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user profile"
        )


@router.patch("/profile", response_model=UserResponse, summary="Update user profile (bulk)")
async def update_user_profile_bulk(
    profile_data: UserProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """
    Update multiple sections of the user profile at once.
    All fields are optional - only provided fields will be updated.
    
    Args:
        profile_data: Fields to update
        
    Returns:
        UserResponse: Updated user profile
    """
    try:
        # Get update data excluding unset fields
        update_data = profile_data.model_dump(exclude_unset=True)
        
        # Update user fields
        for field, value in update_data.items():
            if hasattr(current_user, field):
                setattr(current_user, field, value)
        
        # Save changes
        await db.commit()
        await db.refresh(current_user)
        
        return UserResponse.model_validate(current_user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating user profile: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )


@router.patch("/profile/creator-details", response_model=UserResponse, summary="Update creator details")
async def update_creator_details(
    creator_details: CreatorDetailsUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """
    Update creator-specific details.
    
    Note: This endpoint is only available for users with the 'creator' role.
    
    Args:
        creator_details: Creator-specific information to update
        
    Returns:
        UserResponse: Updated user profile
        
    Raises:
        403: User is not a creator
    """
    if current_user.role != UserRole.CREATOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available for creators"
        )
    
    try:
        # Update creator-specific fields
        update_data = creator_details.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(current_user, field):
                setattr(current_user, field, value)
        
        await db.commit()
        await db.refresh(current_user)
        
        return UserResponse.model_validate(current_user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating creator details: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update creator details"
        )


@router.patch("/profile/company-details", response_model=UserResponse, summary="Update company details")
async def update_company_details(
    company_details: CompanyDetailsUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """
    Update agency/brand company details.
    
    Note: This endpoint is only available for users with 'agency' or 'brand' roles.
    
    Args:
        company_details: Company information to update
        
    Returns:
        UserResponse: Updated user profile
        
    Raises:
        403: User is not an agency or brand
    """
    if current_user.role not in [UserRole.AGENCY, UserRole.BRAND]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available for agencies and brands"
        )
    
    try:
        # Update company-specific fields
        update_data = company_details.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(current_user, field):
                setattr(current_user, field, value)
        
        await db.commit()
        await db.refresh(current_user)
        
        return UserResponse.model_validate(current_user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating company details: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update company details"
        )


@router.post("/profile/verify-phone", summary="Verify phone number")
async def verify_phone_number(
    request: VerificationCodeRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    """
    Verify phone number with SMS code.
    
    Args:
        verification_code: 6-digit verification code sent via SMS
        
    Returns:
        Success message
        
    Raises:
        400: Invalid verification code
        404: No pending verification found
    """
    try:
        # Simplified implementation - in production, verify against stored code
        if len(request.verification_code) != 6 or not request.verification_code.isdigit():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification code format"
            )
            
        return JSONResponse(
            content={"message": "Phone number verified successfully"},
            status_code=status.HTTP_200_OK
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying phone: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify phone number"
        )


@router.post("/profile/request-verification", summary="Request phone verification")
async def request_phone_verification(
    request: PhoneNumberRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    """
    Request phone number verification code via SMS.
    
    Args:
        phone_number: Phone number to verify
        
    Returns:
        Success message with verification details
        
    Raises:
        400: Invalid phone number or too many requests
    """
    try:
        # Simplified implementation - in production, send actual SMS
        logger.info(f"Sending verification code to {request.phone_number}")
        
        return JSONResponse(
            content={
                "message": "Verification code sent",
                "expires_in": 300  # 5 minutes
            },
            status_code=status.HTTP_200_OK
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error requesting verification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification code"
        )


# Admin endpoints
@router.get("/", response_model=UserListResponse, summary="List all users (Admin)")
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    role: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> UserListResponse:
    """
    List all users with pagination and filtering.
    
    Note: This endpoint is only available for admin users.
    
    Args:
        page: Page number (default: 1)
        per_page: Items per page (default: 20, max: 100)
        role: Filter by user role
        search: Search in username, email, or name
        
    Returns:
        UserListResponse: Paginated list of users
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        from sqlalchemy import select, or_, func
        
        # Build query
        query = select(User)
        
        # Apply filters
        if role:
            query = query.where(User.role == role)
        
        if search:
            search_filter = or_(
                User.username.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.first_name.ilike(f"%{search}%"),
                User.last_name.ilike(f"%{search}%")
            )
            query = query.where(search_filter)
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = await db.scalar(count_query)
        
        # Apply pagination
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)
        
        # Execute query
        result = await db.execute(query)
        users = result.scalars().all()
        
        # Calculate pages
        pages = (total + per_page - 1) // per_page
        
        return UserListResponse(
            users=[UserResponse.model_validate(user) for user in users],
            total=total,
            page=page,
            per_page=per_page,
            pages=pages
        )
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list users"
        )