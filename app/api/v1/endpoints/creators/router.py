"""
Creator-specific API endpoints for TikTok Shop Creator CRM
Handles badges, demographics, performance metrics, and creator-specific features.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.db.session import get_db
from app.core.dependencies import get_current_active_user, require_creator_role
from app.models.user import User, UserRole
from app.models.creator import BadgeType
from app.schemas.creator import (
    CreatorBadgeResponse,
    BadgeProgressResponse,
    AllBadgesProgressResponse,
    AudienceDemographicCreate,
    AudienceDemographicResponse,
    AudienceDemographicsBulkUpdate,
    CreatorPerformanceMetrics,
    CreatorRankingResponse,
    CreatorLeaderboardResponse,
    CreatorAnalyticsSummary
)
from app.services.creator_service.creator_service import CreatorService
from app.services.creator_service.badge_service import BadgeService
from app.services.creator_service.analytics_service import CreatorAnalyticsService
from app.core.cache import cache
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/creators",
    tags=["creators"],
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not a creator"},
        404: {"description": "Creator not found"},
        422: {"description": "Validation error"}
    }
)


# Badge endpoints
@router.get("/badges", response_model=List[CreatorBadgeResponse], 
           summary="Get earned badges")
async def get_earned_badges(
    current_user: User = Depends(require_creator_role),
    db: AsyncSession = Depends(get_db)
) -> List[CreatorBadgeResponse]:
    """
    Get all badges earned by the current creator.
    
    Returns:
        List of earned badges with details
    """
    try:
        service = BadgeService(db)
        badges = await service.get_creator_badges(current_user.id)
        
        return [CreatorBadgeResponse.from_orm(badge) for badge in badges]
    except Exception as e:
        logger.error(f"Error fetching badges: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch badges"
        )


@router.get("/badges/progress", response_model=AllBadgesProgressResponse, 
           summary="Get badge progress")
@cache(expire=300)  # Cache for 5 minutes
async def get_badge_progress(
    current_user: User = Depends(require_creator_role),
    db: AsyncSession = Depends(get_db)
) -> AllBadgesProgressResponse:
    """
    Get progress towards all available badges.
    
    Shows:
    - Current GMV
    - Earned badges
    - Progress towards next badges
    - All available badges with progress percentages
    
    Returns:
        AllBadgesProgressResponse: Comprehensive badge progress
    """
    try:
        service = BadgeService(db)
        progress = await service.get_all_badges_progress(current_user.id)
        
        return AllBadgesProgressResponse(**progress)
    except Exception as e:
        logger.error(f"Error fetching badge progress: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch badge progress"
        )


@router.post("/badges/check", summary="Check and award badges")
async def check_and_award_badges(
    current_user: User = Depends(require_creator_role),
    db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    """
    Check current GMV and award any newly earned badges.
    
    This endpoint should be called after GMV updates to ensure
    badges are awarded promptly.
    
    Returns:
        List of newly awarded badges (if any)
    """
    try:
        service = BadgeService(db)
        new_badges = await service.check_and_award_badges(
            creator_id=current_user.id,
            current_gmv=Decimal(str(current_user.total_gmv or 0))  # This would come from actual GMV tracking
        )
        
        if new_badges:
            return JSONResponse(
                content={
                    "message": f"Congratulations! You earned {len(new_badges)} new badge(s)",
                    "badges": [badge.badge_name for badge in new_badges]
                },
                status_code=status.HTTP_200_OK
            )
        else:
            return JSONResponse(
                content={"message": "No new badges earned"},
                status_code=status.HTTP_200_OK
            )
    except Exception as e:
        logger.error(f"Error checking badges: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check badges"
        )


# Audience demographics endpoints
@router.get("/demographics", response_model=List[AudienceDemographicResponse], 
           summary="Get audience demographics")
async def get_audience_demographics(
    current_user: User = Depends(require_creator_role),
    db: AsyncSession = Depends(get_db)
) -> List[AudienceDemographicResponse]:
    """
    Get creator's audience demographic breakdown.
    
    Returns:
        List of demographic segments with percentages
    """
    try:
        service = CreatorService(db)
        demographics = await service.get_audience_demographics(current_user.id)
        
        return [AudienceDemographicResponse.from_orm(demo) for demo in demographics]
    except Exception as e:
        logger.error(f"Error fetching demographics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch demographics"
        )


@router.put("/demographics", response_model=List[AudienceDemographicResponse], 
           summary="Update audience demographics")
async def update_audience_demographics(
    demographics_data: AudienceDemographicsBulkUpdate,
    current_user: User = Depends(require_creator_role),
    db: AsyncSession = Depends(get_db)
) -> List[AudienceDemographicResponse]:
    """
    Update creator's audience demographics.
    
    Note: This replaces all existing demographic data.
    Percentages for each gender must sum to 100%.
    
    Args:
        demographics_data: Complete demographic breakdown
        
    Returns:
        Updated demographic data
    """
    try:
        service = CreatorService(db)
        updated_demographics = await service.update_audience_demographics(
            creator_id=current_user.id,
            demographics=demographics_data.demographics
        )
        
        return [AudienceDemographicResponse.from_orm(demo) for demo in updated_demographics]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating demographics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update demographics"
        )


@router.post("/demographics", response_model=AudienceDemographicResponse, 
            summary="Add single demographic entry")
async def add_demographic_entry(
    demographic: AudienceDemographicCreate,
    current_user: User = Depends(require_creator_role),
    db: AsyncSession = Depends(get_db)
) -> AudienceDemographicResponse:
    """
    Add or update a single demographic entry.
    
    Args:
        demographic: Demographic data to add/update
        
    Returns:
        Created or updated demographic entry
    """
    try:
        service = CreatorService(db)
        result = await service.add_demographic_entry(
            creator_id=current_user.id,
            demographic=demographic
        )
        
        return AudienceDemographicResponse.from_orm(result)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Demographic entry already exists. Use PUT to update all demographics."
        )
    except Exception as e:
        logger.error(f"Error adding demographic: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add demographic entry"
        )


# Performance metrics endpoints
@router.get("/performance", response_model=CreatorPerformanceMetrics, 
           summary="Get performance metrics")
@cache(expire=600)  # Cache for 10 minutes
async def get_performance_metrics(
    time_period: str = Query("all_time", regex="^(today|week|month|year|all_time)$"),
    current_user: User = Depends(require_creator_role),
    db: AsyncSession = Depends(get_db)
) -> CreatorPerformanceMetrics:
    """
    Get creator's performance metrics.
    
    Args:
        time_period: Time period for metrics (today/week/month/year/all_time)
        
    Returns:
        Performance metrics including GMV, conversion rates, etc.
    """
    try:
        service = CreatorAnalyticsService(db)
        metrics = await service.get_performance_metrics(
            creator_id=current_user.id,
            time_period=time_period
        )
        
        return CreatorPerformanceMetrics(**metrics)
    except Exception as e:
        logger.error(f"Error fetching performance metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch performance metrics"
        )


@router.get("/leaderboard", response_model=CreatorLeaderboardResponse, 
           summary="Get creator leaderboard")
@cache(expire=300)  # Cache for 5 minutes
async def get_leaderboard(
    period: str = Query("monthly", regex="^(daily|weekly|monthly|all_time)$"),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> CreatorLeaderboardResponse:
    """
    Get creator leaderboard rankings.
    
    Args:
        period: Time period for rankings
        limit: Number of top creators to return
        
    Returns:
        Leaderboard with top creators and current user's ranking
    """
    try:
        service = CreatorAnalyticsService(db)
        leaderboard = await service.get_leaderboard(
            period=period,
            limit=limit,
            current_user_id=current_user.id if current_user.is_creator else None
        )
        
        return CreatorLeaderboardResponse(**leaderboard)
    except Exception as e:
        logger.error(f"Error fetching leaderboard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch leaderboard"
        )


@router.get("/analytics/summary", response_model=CreatorAnalyticsSummary, 
           summary="Get comprehensive analytics")
async def get_analytics_summary(
    current_user: User = Depends(require_creator_role),
    db: AsyncSession = Depends(get_db)
) -> CreatorAnalyticsSummary:
    """
    Get comprehensive analytics summary for creator.
    
    Includes:
    - Performance metrics
    - Audience demographics
    - Badge progress
    - Current ranking
    
    Returns:
        Complete analytics summary
    """
    try:
        # Fetch all data in parallel for better performance
        creator_service = CreatorService(db)
        badge_service = BadgeService(db)
        analytics_service = CreatorAnalyticsService(db)
        
        # Get all data
        performance = await analytics_service.get_performance_metrics(
            creator_id=current_user.id,
            time_period="all_time"
        )
        demographics = await creator_service.get_audience_demographics(current_user.id)
        badge_progress = await badge_service.get_all_badges_progress(current_user.id)
        ranking = await analytics_service.get_creator_ranking(current_user.id)
        
        return CreatorAnalyticsSummary(
            performance_metrics=CreatorPerformanceMetrics(**performance),
            audience_demographics=[AudienceDemographicResponse.from_orm(d) for d in demographics],
            badge_progress=AllBadgesProgressResponse(**badge_progress),
            ranking=CreatorRankingResponse(**ranking)
        )
    except Exception as e:
        logger.error(f"Error fetching analytics summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch analytics summary"
        )


# Public creator profile endpoint
@router.get("/profile/{creator_id}", response_model=Dict[str, Any], 
           summary="Get public creator profile")
async def get_public_creator_profile(
    creator_id: UUID = Path(..., description="Creator's user ID"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get public creator profile information.
    
    This endpoint is publicly accessible and returns limited information
    suitable for display on creator pages or directories.
    
    Args:
        creator_id: UUID of the creator
        
    Returns:
        Public profile information
    """
    try:
        service = CreatorService(db)
        profile = await service.get_public_profile(creator_id)
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Creator not found"
            )
            
        return profile
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching public profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch creator profile"
        )


# Admin endpoints for creator management
@router.post("/{creator_id}/badges/{badge_type}", summary="Award badge manually (Admin)")
async def award_badge_manually(
    creator_id: UUID = Path(..., description="Creator's user ID"),
    badge_type: BadgeType = Path(..., description="Badge type to award"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    """
    Manually award a badge to a creator.
    
    Note: This endpoint is only available for admin users.
    
    Args:
        creator_id: UUID of the creator
        badge_type: Type of badge to award
        
    Returns:
        Success message
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        service = BadgeService(db)
        badge = await service.award_badge_manually(
            creator_id=creator_id,
            badge_type=badge_type,
            awarded_by=current_user.id
        )
        
        return JSONResponse(
            content={
                "message": f"Badge {badge.badge_name} awarded successfully",
                "badge_id": str(badge.id)
            },
            status_code=status.HTTP_201_CREATED
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error awarding badge: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to award badge"
        )