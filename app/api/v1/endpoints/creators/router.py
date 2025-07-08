"""
Creator-specific API endpoints for TikTok Shop Creator CRM
Handles creator profiles, demographics, and integrates with badge system.
"""
##app/core/api/v1/endpoints/creators/router.py
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from pydantic import EmailStr

from app.db.session import get_db
from app.core.dependencies import get_current_active_user, require_creator_role
from app.models.user import User, UserRole
from app.schemas.creator import (
    AudienceDemographicCreate,
    AudienceDemographicResponse,
    AudienceDemographicsBulkUpdate,
    CreatorPerformanceMetrics,
    CreatorRankingResponse,
    CreatorLeaderboardResponse,
    CreatorAnalyticsSummary,
    CreatorProfileResponse,
    # NEW demographics schemas
    DemographicsVisualizationData,
    DemographicsAnalytics,
    CreatorDemographicsProfile
)
from app.schemas.badge import (
    BadgeResponse,
    BadgeProgressResponse,
    BadgeHistoryResponse,
    BadgeShowcaseResponse
)
from app.services.creator_service.creator_service import CreatorService
from app.services.badge_service import BadgeService, ProgressTracker
from app.services.creator_service.analytics_service import CreatorAnalyticsService
from app.services.demographics import DemographicsVisualizationService
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


# Profile endpoints (EXISTING - NO CHANGES)
@router.get("/profile", response_model=CreatorProfileResponse, 
           summary="Get current creator's profile")
async def get_creator_profile(
    current_user: User = Depends(require_creator_role),
    db: AsyncSession = Depends(get_db)
) -> CreatorProfileResponse:
    """
    Get comprehensive profile for the current creator including badges.
    
    Returns:
        Complete creator profile with performance metrics and badges
    """
    try:
        creator_service = CreatorService(db)
        badge_service = BadgeService(db)
        
        # Get basic profile
        creator = await creator_service.get_creator_by_id(current_user.id)
        if not creator:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Creator profile not found"
            )
        
        # Get badges
        badges = await badge_service.get_creator_badges(current_user.id)
        
        # Get badge progress
        progress_tracker = ProgressTracker(db)
        badge_progress = await progress_tracker.get_overall_progress(current_user.id)
        
        # Construct response
        return CreatorProfileResponse(
            id=creator.id,
            username=creator.username,
            email=creator.email,
            first_name=creator.first_name,
            last_name=creator.last_name,
            profile_image_url=creator.profile_image_url,
            bio=creator.bio,
            content_niche=creator.content_niche,
            follower_count=creator.follower_count,
            average_views=creator.average_views,
            engagement_rate=float(creator.engagement_rate) if creator.engagement_rate else None,
            current_gmv=float(creator.current_gmv or 0),
            tiktok_handle=creator.tiktok_handle,
            instagram_handle=creator.instagram_handle,
            discord_handle=creator.discord_handle,
            badges=badges,
            badge_progress=badge_progress,
            total_campaigns=0,  # TODO: Implement when campaigns are ready
            completion_rate=0.0,  # TODO: Implement when campaigns are ready
            avg_rating=None,  # TODO: Implement when ratings are ready
            created_at=creator.created_at,
            last_active=creator.last_login,
            is_verified=creator.email_verified
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching creator profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch creator profile"
        )


# Badge endpoints (EXISTING - NO CHANGES)
@router.get("/badges", response_model=List[BadgeResponse], 
           summary="Get creator's badges")
async def get_creator_badges(
    current_user: User = Depends(require_creator_role),
    db: AsyncSession = Depends(get_db)
) -> List[BadgeResponse]:
    """
    Get all badges (earned and unearned) for the current creator.
    
    Returns:
        List of all badges with status and progress
    """
    try:
        badge_service = BadgeService(db)
        return await badge_service.get_creator_badges(current_user.id)
        
    except Exception as e:
        logger.error(f"Error fetching badges: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch badges"
        )


@router.get("/badges/progress", response_model=BadgeProgressResponse, 
           summary="Get badge progress")
@cache(expire=300)  # Cache for 5 minutes
async def get_badge_progress(
    current_user: User = Depends(require_creator_role),
    db: AsyncSession = Depends(get_db)
) -> BadgeProgressResponse:
    """
    Get overall badge progress for the current creator.
    
    Returns:
        Progress information including next badge details
    """
    try:
        progress_tracker = ProgressTracker(db)
        return await progress_tracker.get_overall_progress(current_user.id)
        
    except Exception as e:
        logger.error(f"Error fetching badge progress: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch badge progress"
        )


@router.get("/badges/history", response_model=List[BadgeHistoryResponse], 
           summary="Get badge history")
async def get_badge_history(
    current_user: User = Depends(require_creator_role),
    db: AsyncSession = Depends(get_db)
) -> List[BadgeHistoryResponse]:
    """
    Get badge achievement history for the current creator.
    
    Returns:
        List of badge achievements with dates
    """
    try:
        badge_service = BadgeService(db)
        return await badge_service.get_badge_history(current_user.id)
        
    except Exception as e:
        logger.error(f"Error fetching badge history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch badge history"
        )


@router.get("/badges/showcase", response_model=BadgeShowcaseResponse, 
           summary="Get badge showcase")
async def get_badge_showcase(
    current_user: User = Depends(require_creator_role),
    db: AsyncSession = Depends(get_db)
) -> BadgeShowcaseResponse:
    """
    Get badge showcase data for profile display.
    
    Returns:
        Featured badges and achievement summary
    """
    try:
        badge_service = BadgeService(db)
        progress_tracker = ProgressTracker(db)
        
        # Get all badges
        badges = await badge_service.get_creator_badges(current_user.id)
        earned_badges = [b for b in badges if b.status == "earned"]
        
        # Get recent achievement
        history = await badge_service.get_badge_history(current_user.id)
        recent = history[0] if history else None
        
        # Get highest tier
        highest_tier = None
        if earned_badges:
            earned_badges.sort(key=lambda x: x.gmv_requirement, reverse=True)
            highest_tier = earned_badges[0].tier
        
        return BadgeShowcaseResponse(
            featured_badges=earned_badges[:3],  # Top 3 badges
            total_earned=len(earned_badges),
            highest_tier=highest_tier,
            recent_achievement=recent
        )
        
    except Exception as e:
        logger.error(f"Error fetching badge showcase: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch badge showcase"
        )


# Audience Demographics endpoints (ENHANCED)
@router.get("/demographics", response_model=List[AudienceDemographicResponse],
           summary="Get audience demographics")
async def get_audience_demographics(
    current_user: User = Depends(require_creator_role),
    db: AsyncSession = Depends(get_db)
) -> List[AudienceDemographicResponse]:
    """
    Get audience demographics for the current creator.
    
    Returns:
        List of demographic breakdowns
    """
    try:
        creator_service = CreatorService(db)
        return await creator_service.get_audience_demographics(current_user.id)
        
    except Exception as e:
        logger.error(f"Error fetching demographics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch audience demographics"
        )


@router.put("/demographics/bulk", response_model=List[AudienceDemographicResponse],
           summary="Bulk update demographics")
async def bulk_update_demographics(
    demographics: AudienceDemographicsBulkUpdate,
    current_user: User = Depends(require_creator_role),
    db: AsyncSession = Depends(get_db)
) -> List[AudienceDemographicResponse]:
    """
    Bulk update audience demographics.
    
    Args:
        demographics: List of demographic entries (must sum to ~100%)
        
    Returns:
        Updated demographic list
    """
    try:
        creator_service = CreatorService(db)
        return await creator_service.update_audience_demographics(
            current_user.id,
            demographics.demographics
        )
        
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


# NEW: Enhanced demographics endpoints
@router.get("/demographics/visualization", 
           response_model=DemographicsVisualizationData,
           summary="Get demographics visualization data")
@cache(expire=300)
async def get_demographics_visualization(
    current_user: User = Depends(require_creator_role),
    db: AsyncSession = Depends(get_db)
) -> DemographicsVisualizationData:
    """
    Get demographics data formatted for visualization charts.
    
    Returns:
        Data formatted for gender, age, and location charts
    """
    try:
        creator_service = CreatorService(db)
        viz_data = await creator_service.get_demographics_visualization_data(current_user.id)
        return viz_data
        
    except Exception as e:
        logger.error(f"Error getting visualization data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get visualization data"
        )


@router.get("/demographics/analytics",
           response_model=DemographicsAnalytics,
           summary="Get demographics analytics")
async def get_demographics_analytics(
    period_days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(require_creator_role),
    db: AsyncSession = Depends(get_db)
) -> DemographicsAnalytics:
    """
    Get analytics for audience demographics.
    
    Args:
        period_days: Period for analytics (default 30 days)
        
    Returns:
        Analytics including engagement by demographic
    """
    try:
        analytics_service = CreatorAnalyticsService(db)
        analytics = await analytics_service.get_demographics_analytics(
            current_user.id,
            period_days
        )
        return analytics
        
    except Exception as e:
        logger.error(f"Error getting demographics analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get demographics analytics"
        )


@router.get("/demographics/profile",
           response_model=CreatorDemographicsProfile,
           summary="Get complete demographics profile")
async def get_demographics_profile(
    current_user: User = Depends(require_creator_role),
    db: AsyncSession = Depends(get_db)
) -> CreatorDemographicsProfile:
    """
    Get complete demographics profile including visualization and analytics.
    
    Returns:
        Comprehensive demographics profile
    """
    try:
        creator_service = CreatorService(db)
        analytics_service = CreatorAnalyticsService(db)
        
        # Get all demographics data
        demographics = await creator_service.get_audience_demographics(current_user.id)
        viz_data = await creator_service.get_demographics_visualization_data(current_user.id)
        analytics = await analytics_service.get_demographics_analytics(current_user.id, 30)
        
        # Calculate completeness
        completeness = await creator_service.calculate_demographics_completeness(current_user.id)
        
        return CreatorDemographicsProfile(
            creator_id=current_user.id,
            demographics=demographics,
            visualization_data=viz_data,
            analytics=analytics,
            last_updated=datetime.utcnow(),
            completeness_score=completeness
        )
        
    except Exception as e:
        logger.error(f"Error getting demographics profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get demographics profile"
        )


# Performance metrics endpoints (EXISTING - NO CHANGES)
@router.get("/performance", response_model=CreatorPerformanceMetrics,
           summary="Get performance metrics")
@cache(expire=600)  # Cache for 10 minutes
async def get_performance_metrics(
    current_user: User = Depends(require_creator_role),
    db: AsyncSession = Depends(get_db)
) -> CreatorPerformanceMetrics:
    """
    Get comprehensive performance metrics for the current creator.
    
    Returns:
        Performance metrics including GMV, campaigns, and badges
    """
    try:
        analytics_service = CreatorAnalyticsService(db)
        badge_service = BadgeService(db)
        progress_tracker = ProgressTracker(db)
        
        # Get performance metrics
        metrics = await analytics_service.get_performance_metrics(current_user.id)
        
        # Get badge info
        badges = await badge_service.get_creator_badges(current_user.id)
        earned_badges = [b for b in badges if b.status == "earned"]
        
        # Get highest badge
        highest_badge = None
        if earned_badges:
            earned_badges.sort(key=lambda x: x.gmv_requirement, reverse=True)
            highest_badge = earned_badges[0].name
        
        # Get next badge progress
        progress = await progress_tracker.get_overall_progress(current_user.id)
        
        # Build response
        return CreatorPerformanceMetrics(
            creator_id=current_user.id,
            total_gmv=float(metrics['total_gmv']),
            average_order_value=float(metrics['average_order_value']),
            conversion_rate=metrics['conversion_rate'],
            total_orders=metrics['total_orders'],
            total_campaigns=metrics['total_campaigns'],
            active_campaigns=metrics['active_campaigns'],
            completion_rate=0.0,  # TODO: Calculate from campaigns
            avg_engagement_rate=metrics['engagement_rate'],
            badges_earned=len(earned_badges),
            highest_badge=highest_badge,
            next_badge_progress=progress.progress_percentage,
            gmv_last_30_days=0.0,  # TODO: Calculate from orders
            gmv_growth_rate=0.0  # TODO: Calculate trend
        )
        
    except Exception as e:
        logger.error(f"Error fetching performance metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch performance metrics"
        )


# Analytics endpoints (EXISTING - NO CHANGES)
@router.get("/analytics/summary", response_model=CreatorAnalyticsSummary,
           summary="Get analytics summary")
async def get_analytics_summary(
    period_days: int = Query(30, ge=1, le=365, description="Period in days"),
    current_user: User = Depends(require_creator_role),
    db: AsyncSession = Depends(get_db)
) -> CreatorAnalyticsSummary:
    """
    Get analytics summary for specified period.
    
    Args:
        period_days: Number of days to analyze (1-365)
        
    Returns:
        Comprehensive analytics summary
    """
    try:
        analytics_service = CreatorAnalyticsService(db)
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=period_days)
        
        return await analytics_service.get_analytics_summary(
            current_user.id,
            start_date,
            end_date
        )
        
    except Exception as e:
        logger.error(f"Error fetching analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch analytics"
        )


# Leaderboard endpoints (EXISTING - NO CHANGES)
@router.get("/leaderboard", response_model=CreatorLeaderboardResponse,
           summary="Get creator leaderboard")
@cache(expire=1800)  # Cache for 30 minutes
async def get_creator_leaderboard(
    period: str = Query("all-time", regex="^(weekly|monthly|all-time)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
) -> CreatorLeaderboardResponse:
    """
    Get creator leaderboard based on GMV and badges.
    
    Args:
        period: Leaderboard period (weekly, monthly, all-time)
        limit: Number of creators to return
        offset: Pagination offset
        
    Returns:
        Leaderboard with creator rankings
    """
    try:
        analytics_service = CreatorAnalyticsService(db)
        
        leaderboard_data = await analytics_service.get_creator_leaderboard(
            period=period,
            limit=limit,
            offset=offset
        )
        
        return CreatorLeaderboardResponse(
            period=period,
            updated_at=datetime.utcnow(),
            total_creators=leaderboard_data["total"],
            leaderboard=leaderboard_data["creators"]
        )
        
    except Exception as e:
        logger.error(f"Error fetching leaderboard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch leaderboard"
        )


# Search creators (EXISTING - NO CHANGES)
@router.get("/search", response_model=List[CreatorProfileResponse],
           summary="Search creators")
async def search_creators(
    content_niche: Optional[str] = Query(None, description="Filter by niche"),
    min_followers: Optional[int] = Query(None, ge=0, description="Minimum followers"),
    min_engagement_rate: Optional[float] = Query(None, ge=0, le=100),
    has_badge: Optional[str] = Query(None, description="Filter by badge type"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> List[CreatorProfileResponse]:
    """
    Search creators with filters (for agencies and brands).
    
    Args:
        content_niche: Filter by content niche
        min_followers: Minimum follower count
        min_engagement_rate: Minimum engagement rate
        has_badge: Filter by specific badge type
        limit: Number of results
        offset: Pagination offset
        
    Returns:
        List of creator profiles matching criteria
    """
    try:
        # Only agencies and brands can search creators
        if current_user.role not in [UserRole.agency, UserRole.brand, UserRole.admin]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only agencies and brands can search creators"
            )
        
        creator_service = CreatorService(db)
        
        # Search creators
        search_results = await creator_service.search_creators(
            content_niche=content_niche,
            min_followers=min_followers,
            has_badges=has_badge is not None,
            page=(offset // limit) + 1,
            per_page=limit
        )
        
        # Convert to response format with badges
        results = []
        badge_service = BadgeService(db)
        
        for creator_data in search_results['creators']:
            if creator_data:  # creator_data might be None
                creator_id = UUID(creator_data['id'])
                
                # Get creator full data
                creator = await creator_service.get_creator_by_id(creator_id)
                if creator:
                    badges = await badge_service.get_creator_badges(creator_id)
                    
                    results.append(CreatorProfileResponse(
                        id=creator.id,
                        username=creator.username,
                        email=creator.email,
                        first_name=creator.first_name,
                        last_name=creator.last_name,
                        profile_image_url=creator.profile_image_url,
                        bio=creator.bio,
                        content_niche=creator.content_niche,
                        follower_count=creator.follower_count,
                        average_views=creator.average_views,
                        engagement_rate=float(creator.engagement_rate) if creator.engagement_rate else None,
                        current_gmv=float(creator.current_gmv or 0),
                        tiktok_handle=creator.tiktok_handle,
                        instagram_handle=creator.instagram_handle,
                        discord_handle=creator.discord_handle,
                        badges=[b for b in badges if b.status == "earned"],
                        badge_progress=None,  # Don't include progress for search results
                        total_campaigns=0,
                        completion_rate=0.0,
                        avg_rating=None,
                        created_at=creator.created_at,
                        last_active=creator.last_login,
                        is_verified=creator.email_verified
                    ))
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching creators: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search creators"
        )