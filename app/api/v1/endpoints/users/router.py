"""
User profile API endpoints for TikTok Shop Creator CRM
Handles profile management, updates, and completion tracking for all user types.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.db.session import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
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
from app.services.user_service.profile_service import ProfileService
from app.core.dependencies import has_permission
from app.utils.logging import get_logger


logger = get_logger(__name__)

router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized"},
        404: {"description": "User not found"},
        422: {"description": "Validation error"}
    }
)


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
        service = ProfileService(db)
        user_data = await service.get_user_profile(current_user.id)
        return UserResponse.from_orm(user_data)
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
    if str(user_id) != str(current_user.id) and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this profile"
        )
    
    try:
        service = ProfileService(db)
        user_data = await service.get_user_profile(user_id)
        
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
            
        return UserResponse.from_orm(user_data)
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
        service = ProfileService(db)
        updated_user = await service.update_profile_bulk(
            user_id=current_user.id,
            update_data=profile_data.dict(exclude_unset=True)
        )
        
        return UserResponse.from_orm(updated_user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating user profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )


@router.patch("/profile/personal", response_model=UserResponse, summary="Update personal information")
async def update_personal_info(
    personal_info: PersonalInfoUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """
    Update user's personal information section.
    
    This includes:
    - Phone number
    - Date of birth
    - Gender
    - Profile image URL
    - Bio
    
    Args:
        personal_info: Personal information to update
        
    Returns:
        UserResponse: Updated user profile
    """
    try:
        service = ProfileService(db)
        updated_user = await service.update_personal_info(
            user_id=current_user.id,
            personal_info=personal_info
        )
        
        return UserResponse.from_orm(updated_user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating personal info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update personal information"
        )


@router.patch("/profile/address", response_model=UserResponse, summary="Update shipping address")
async def update_address(
    address_info: AddressUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """
    Update user's shipping address.
    
    Note: If any address field is provided, all required fields must be included
    (address_line1, city, state, postal_code) to ensure complete shipping information.
    
    Args:
        address_info: Address information to update
        
    Returns:
        UserResponse: Updated user profile
    """
    try:
        service = ProfileService(db)
        updated_user = await service.update_address(
            user_id=current_user.id,
            address_info=address_info
        )
        
        return UserResponse.from_orm(updated_user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating address: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update address"
        )


@router.patch("/profile/social", response_model=UserResponse, summary="Update social media handles")
async def update_social_media(
    social_info: SocialMediaUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """
    Update user's social media handles.
    
    Handles are automatically normalized:
    - @ symbols are removed from TikTok and Instagram handles
    - Discord handles can be in username#0000 or username format
    
    Args:
        social_info: Social media handles to update
        
    Returns:
        UserResponse: Updated user profile
    """
    try:
        service = ProfileService(db)
        updated_user = await service.update_social_media(
            user_id=current_user.id,
            social_info=social_info
        )
        
        return UserResponse.from_orm(updated_user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating social media: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update social media handles"
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
    if not current_user.is_creator:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available for creators"
        )
    
    try:
        service = ProfileService(db)
        updated_user = await service.update_creator_details(
            user_id=current_user.id,
            creator_details=creator_details
        )
        
        return UserResponse.from_orm(updated_user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating creator details: {str(e)}")
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
    if not (current_user.is_agency or current_user.is_brand):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available for agencies and brands"
        )
    
    try:
        service = ProfileService(db)
        updated_user = await service.update_company_details(
            user_id=current_user.id,
            company_details=company_details
        )
        
        return UserResponse.from_orm(updated_user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating company details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update company details"
        )


@router.patch("/preferences", response_model=UserResponse, summary="Update notification preferences")
async def update_preferences(
    preferences: NotificationPreferences,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """
    Update user's notification preferences.
    
    Args:
        preferences: Notification preferences to update
        
    Returns:
        UserResponse: Updated user profile
    """
    try:
        service = ProfileService(db)
        updated_user = await service.update_preferences(
            user_id=current_user.id,
            preferences=preferences.dict()
        )
        
        return UserResponse.from_orm(updated_user)
    except Exception as e:
        logger.error(f"Error updating preferences: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update preferences"
        )


@router.get("/profile/completion", response_model=ProfileCompletionStatus, 
           summary="Get profile completion status")
async def get_profile_completion(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> ProfileCompletionStatus:
    """
    Get detailed profile completion status.
    
    Returns information about:
    - Overall completion percentage
    - Missing fields
    - Completed sections
    - Suggested next steps
    
    Returns:
        ProfileCompletionStatus: Detailed completion information
    """
    try:
        service = ProfileService(db)
        completion_status = await service.get_profile_completion_status(current_user.id)
        
        return ProfileCompletionStatus(**completion_status)
    except Exception as e:
        logger.error(f"Error getting profile completion: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get profile completion status"
        )


@router.post("/profile/verify-phone", summary="Verify phone number")
async def verify_phone_number(
    verification_code: str = Body(..., embed=True),
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
        service = ProfileService(db)
        result = await service.verify_phone_number(
            user_id=current_user.id,
            code=verification_code
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification code"
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
    phone_number: str = Body(..., embed=True, regex=r'^\+?1?\d{9,15}$'),
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
        service = ProfileService(db)
        result = await service.request_phone_verification(
            user_id=current_user.id,
            phone_number=phone_number
        )
        
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
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        service = ProfileService(db)
        result = await service.list_users(
            page=page,
            per_page=per_page,
            role=role,
            search=search
        )
        
        return UserListResponse(**result)
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list users"
        )