"""
Badge API Endpoints
Handles all badge-related HTTP requests
"""
##app/core/api/v1/endpoints/badges/router.py
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.badge import (
    BadgeResponse,
    BadgeProgressResponse,
    BadgeHistoryResponse,
    BadgeStatsResponse,
    PaceEstimateResponse,
    BadgeShowcaseResponse,
    CreatorBadgesSummary
)
from app.services.badge_service import (
    BadgeService,
    ProgressTracker,
    PaceEstimator
)
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/", response_model=List[BadgeResponse])
async def get_all_badges(
    db: AsyncSession = Depends(get_db)
) -> List[BadgeResponse]:
    """
    Get all available badges in the system
    
    Returns:
        List of all badge types with their requirements
    """
    try:
        from app.utils.badge_constants import BADGE_TIERS
        
        badges = []
        for tier in BADGE_TIERS:
            badges.append(BadgeResponse(
                id=tier.badge_type,
                badge_type=tier.badge_type,
                name=tier.name,
                description=tier.description,
                tier=tier.tier,
                gmv_requirement=float(tier.gmv_threshold),
                status="available",
                progress=0.0,
                earned_date=None,
                icon=tier.icon,
                color=tier.color,
                bg_color=tier.bg_color
            ))
        
        return badges
        
    except Exception as e:
        logger.error(f"Error fetching badge types: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch badge types"
        )


@router.get("/stats", response_model=BadgeStatsResponse)
async def get_badge_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> BadgeStatsResponse:
    """
    Get network-wide badge statistics
    
    Returns:
        Badge distribution and statistics
    """
    try:
        badge_service = BadgeService(db)
        return await badge_service.get_network_badge_stats()
        
    except Exception as e:
        logger.error(f"Error fetching badge stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch badge statistics"
        )


@router.get("/creator/{creator_id}", response_model=List[BadgeResponse])
async def get_creator_badges(
    creator_id: UUID = Path(..., description="Creator UUID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> List[BadgeResponse]:
    """
    Get all badges for a specific creator
    
    Args:
        creator_id: UUID of the creator
        
    Returns:
        List of creator's badges with status
    """
    try:
        badge_service = BadgeService(db)
        return await badge_service.get_creator_badges(creator_id)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error fetching creator badges: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch creator badges"
        )


@router.get("/creator/{creator_id}/progress", response_model=BadgeProgressResponse)
async def get_creator_badge_progress(
    creator_id: UUID = Path(..., description="Creator UUID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> BadgeProgressResponse:
    """
    Get overall badge progress for a creator
    
    Args:
        creator_id: UUID of the creator
        
    Returns:
        Overall progress information
    """
    try:
        progress_tracker = ProgressTracker(db)
        return await progress_tracker.get_overall_progress(creator_id)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error fetching badge progress: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch badge progress"
        )


@router.get("/creator/{creator_id}/history", response_model=List[BadgeHistoryResponse])
async def get_creator_badge_history(
    creator_id: UUID = Path(..., description="Creator UUID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> List[BadgeHistoryResponse]:
    """
    Get badge achievement history for a creator
    
    Args:
        creator_id: UUID of the creator
        
    Returns:
        List of badge achievements with dates
    """
    try:
        badge_service = BadgeService(db)
        return await badge_service.get_badge_history(creator_id)
        
    except Exception as e:
        logger.error(f"Error fetching badge history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch badge history"
        )


@router.get("/creator/{creator_id}/showcase", response_model=BadgeShowcaseResponse)
async def get_creator_badge_showcase(
    creator_id: UUID = Path(..., description="Creator UUID"),
    db: AsyncSession = Depends(get_db)
) -> BadgeShowcaseResponse:
    """
    Get badge showcase for profile display
    
    Args:
        creator_id: UUID of the creator
        
    Returns:
        Badge showcase data for profile
    """
    try:
        badge_service = BadgeService(db)
        progress_tracker = ProgressTracker(db)
        
        # Get all badges
        badges = await badge_service.get_creator_badges(creator_id)
        earned_badges = [b for b in badges if b.status == "earned"]
        
        # Get recent achievement
        history = await badge_service.get_badge_history(creator_id)
        recent = history[0] if history else None
        
        # Get highest tier
        highest_tier = None
        if earned_badges:
            # Sort by GMV requirement to find highest
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


@router.get("/creator/{creator_id}/pace", response_model=List[PaceEstimateResponse])
async def get_badge_pace_estimates(
    creator_id: UUID = Path(..., description="Creator UUID"),
    lookback_days: int = Query(30, ge=7, le=365, description="Days to analyze"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> List[PaceEstimateResponse]:
    """
    Get pace estimates for achieving badges
    
    Args:
        creator_id: UUID of the creator
        lookback_days: Number of days to analyze for pace
        
    Returns:
        List of pace estimates for unearned badges
    """
    try:
        pace_estimator = PaceEstimator(db)
        return await pace_estimator.estimate_all_badges(creator_id, lookback_days)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error calculating badge pace: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate badge pace"
        )


@router.get("/creator/{creator_id}/pace/{badge_type}", response_model=PaceEstimateResponse)
async def get_specific_badge_pace(
    creator_id: UUID = Path(..., description="Creator UUID"),
    badge_type: str = Path(..., description="Badge type"),
    lookback_days: int = Query(30, ge=7, le=365, description="Days to analyze"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> PaceEstimateResponse:
    """
    Get pace estimate for a specific badge
    
    Args:
        creator_id: UUID of the creator
        badge_type: Type of badge to estimate
        lookback_days: Number of days to analyze
        
    Returns:
        Pace estimate for the specific badge
    """
    try:
        pace_estimator = PaceEstimator(db)
        return await pace_estimator.estimate_time_to_badge(
            creator_id, 
            badge_type, 
            lookback_days
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error calculating badge pace: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate badge pace"
        )


@router.post("/calculate/{creator_id}")
async def calculate_creator_badges(
    creator_id: UUID = Path(..., description="Creator UUID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> dict:
    """
    Trigger badge calculation for a creator (Admin only)
    
    Args:
        creator_id: UUID of the creator
        
    Returns:
        Calculation result
    """
    try:
        # Check if user is admin
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can trigger badge calculations"
            )
        
        from app.services.badge_service import GMVCalculator
        
        badge_service = BadgeService(db)
        gmv_calculator = GMVCalculator(db)
        
        # Calculate current GMV
        current_gmv = await gmv_calculator.calculate_total_gmv(creator_id)
        
        # Check and assign badges
        new_badges = await badge_service.check_and_assign_badges(creator_id, current_gmv)
        
        return {
            "status": "success",
            "current_gmv": float(current_gmv),
            "new_badges_assigned": len(new_badges),
            "badges": [
                {
                    "type": badge.badge_type,
                    "name": badge.badge_name,
                    "earned_at": badge.earned_at
                }
                for badge in new_badges
            ]
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error calculating badges: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate badges"
        )


@router.get("/leaderboard", response_model=List[CreatorBadgesSummary])
async def get_badge_leaderboard(
    limit: int = Query(10, ge=1, le=100, description="Number of creators to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db)
) -> List[CreatorBadgesSummary]:
    """
    Get leaderboard of creators by badges earned
    
    Args:
        limit: Number of results to return
        offset: Pagination offset
        
    Returns:
        List of creators sorted by badge achievements
    """
    try:
        from sqlalchemy import select, func, desc
        from app.models.badge import CreatorBadge
        
        # Query to get creators with badge counts
        query = (
            select(
                User.id,
                User.username,
                User.current_gmv,
                func.count(CreatorBadge.id).label("badge_count"),
                func.array_agg(CreatorBadge.badge_type).label("badge_types")
            )
            .join(CreatorBadge, User.id == CreatorBadge.creator_id)
            .where(User.role == "creator")
            .group_by(User.id, User.username, User.current_gmv)
            .order_by(desc("badge_count"), desc(User.current_gmv))
            .limit(limit)
            .offset(offset)
        )
        
        result = await db.execute(query)
        rows = result.all()
        
        summaries = []
        for row in rows:
            # Find highest badge
            badge_types = row.badge_types or []
            highest_badge = None
            if badge_types:
                from app.utils.badge_constants import BADGE_TIERS
                # Sort by GMV threshold to find highest
                for tier in reversed(BADGE_TIERS):
                    if tier.badge_type in badge_types:
                        highest_badge = tier.name
                        break
            
            summaries.append(CreatorBadgesSummary(
                creator_id=row.id,
                username=row.username,
                total_gmv=float(row.current_gmv or 0),
                badges_earned=row.badge_count,
                highest_badge=highest_badge,
                badges=badge_types
            ))
        
        return summaries
        
    except Exception as e:
        logger.error(f"Error fetching badge leaderboard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch badge leaderboard"
        )