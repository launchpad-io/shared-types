"""
Progress Tracker Service
Tracks badge progress and calculates completion percentages
"""

from typing import Optional, Dict, List
from uuid import UUID
from decimal import Decimal
from datetime import datetime

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.badge import CreatorBadge
from app.utils.badge_constants import BADGE_TIERS, BadgeTier
from app.schemas.badge import BadgeProgressResponse, ProgressDetails
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ProgressTracker:
    """Service for tracking badge progress and milestones"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_overall_progress(self, creator_id: UUID) -> BadgeProgressResponse:
        """
        Get overall badge progress for a creator
        
        Args:
            creator_id: UUID of the creator
            
        Returns:
            Overall progress response
        """
        try:
            # Get creator with badges
            result = await self.session.execute(
                select(User)
                .options(selectinload(User.badges))
                .where(User.id == creator_id)
            )
            creator = result.scalar_one_or_none()
            
            if not creator:
                raise ValueError(f"Creator {creator_id} not found")
            
            current_gmv = creator.current_gmv or Decimal(0)
            earned_badges = {badge.badge_type for badge in creator.badges}
            
            # Find next badge
            next_badge = None
            next_tier = None
            for tier in BADGE_TIERS:
                if tier.badge_type not in earned_badges and current_gmv < tier.gmv_threshold:
                    next_badge = tier
                    next_tier = tier
                    break
            
            # Calculate progress
            if next_badge:
                progress_percentage = float(
                    (current_gmv / next_badge.gmv_threshold) * 100
                )
                remaining_gmv = next_badge.gmv_threshold - current_gmv
            else:
                # All badges earned
                progress_percentage = 100.0
                remaining_gmv = Decimal(0)
            
            # Get current badge (highest earned)
            current_badge = None
            for tier in reversed(BADGE_TIERS):
                if tier.badge_type in earned_badges:
                    current_badge = tier
                    break
            
            return BadgeProgressResponse(
                creator_id=creator_id,
                current_gmv=float(current_gmv),
                total_badges_earned=len(earned_badges),
                total_badges_available=len(BADGE_TIERS),
                next_badge_type=next_badge.badge_type if next_badge else None,
                next_badge_name=next_badge.name if next_badge else None,
                next_badge_threshold=float(next_badge.gmv_threshold) if next_badge else None,
                progress_percentage=progress_percentage,
                remaining_gmv=float(remaining_gmv),
                current_badge_type=current_badge.badge_type if current_badge else None,
                current_badge_name=current_badge.name if current_badge else None
            )
            
        except Exception as e:
            logger.error(f"Error getting overall progress: {str(e)}")
            raise
    
    async def get_badge_specific_progress(
        self, 
        creator_id: UUID, 
        badge_type: str
    ) -> ProgressDetails:
        """
        Get progress toward a specific badge
        
        Args:
            creator_id: UUID of the creator
            badge_type: Type of badge to check progress for
            
        Returns:
            Detailed progress information
        """
        try:
            # Get creator
            result = await self.session.execute(
                select(User)
                .where(User.id == creator_id)
            )
            creator = result.scalar_one_or_none()
            
            if not creator:
                raise ValueError(f"Creator {creator_id} not found")
            
            # Find badge tier
            tier = next((t for t in BADGE_TIERS if t.badge_type == badge_type), None)
            if not tier:
                raise ValueError(f"Invalid badge type: {badge_type}")
            
            current_gmv = creator.current_gmv or Decimal(0)
            
            # Check if already earned
            badge_result = await self.session.execute(
                select(CreatorBadge)
                .where(
                    and_(
                        CreatorBadge.creator_id == creator_id,
                        CreatorBadge.badge_type == badge_type
                    )
                )
            )
            earned_badge = badge_result.scalar_one_or_none()
            
            if earned_badge:
                return ProgressDetails(
                    badge_type=badge_type,
                    badge_name=tier.name,
                    is_earned=True,
                    earned_date=earned_badge.earned_at,
                    progress_percentage=100.0,
                    current_value=float(current_gmv),
                    threshold_value=float(tier.gmv_threshold),
                    remaining_value=0.0
                )
            
            # Calculate progress
            progress = float((current_gmv / tier.gmv_threshold) * 100)
            remaining = tier.gmv_threshold - current_gmv
            
            return ProgressDetails(
                badge_type=badge_type,
                badge_name=tier.name,
                is_earned=False,
                earned_date=None,
                progress_percentage=min(progress, 99.9),  # Cap at 99.9% if not earned
                current_value=float(current_gmv),
                threshold_value=float(tier.gmv_threshold),
                remaining_value=float(remaining)
            )
            
        except Exception as e:
            logger.error(f"Error getting badge progress: {str(e)}")
            raise
    
    async def get_milestone_progress(self, creator_id: UUID) -> List[Dict[str, any]]:
        """
        Get progress toward all milestones
        
        Args:
            creator_id: UUID of the creator
            
        Returns:
            List of milestone progress details
        """
        try:
            milestones = []
            
            for tier in BADGE_TIERS:
                progress = await self.get_badge_specific_progress(creator_id, tier.badge_type)
                milestones.append({
                    "badge_type": tier.badge_type,
                    "name": tier.name,
                    "tier": tier.tier,
                    "threshold": float(tier.gmv_threshold),
                    "progress": progress.progress_percentage,
                    "is_earned": progress.is_earned,
                    "earned_date": progress.earned_date,
                    "icon": tier.icon,
                    "color": tier.color
                })
            
            return milestones
            
        except Exception as e:
            logger.error(f"Error getting milestone progress: {str(e)}")
            raise
    
    async def get_next_milestones(
        self, 
        creator_id: UUID, 
        limit: int = 3
    ) -> List[Dict[str, any]]:
        """
        Get the next upcoming milestones for a creator
        
        Args:
            creator_id: UUID of the creator
            limit: Number of milestones to return
            
        Returns:
            List of upcoming milestones
        """
        try:
            # Get creator with badges
            result = await self.session.execute(
                select(User)
                .options(selectinload(User.badges))
                .where(User.id == creator_id)
            )
            creator = result.scalar_one_or_none()
            
            if not creator:
                raise ValueError(f"Creator {creator_id} not found")
            
            current_gmv = creator.current_gmv or Decimal(0)
            earned_types = {badge.badge_type for badge in creator.badges}
            
            # Find unearned badges
            upcoming = []
            for tier in BADGE_TIERS:
                if tier.badge_type not in earned_types:
                    progress = float((current_gmv / tier.gmv_threshold) * 100)
                    upcoming.append({
                        "badge_type": tier.badge_type,
                        "name": tier.name,
                        "tier": tier.tier,
                        "threshold": float(tier.gmv_threshold),
                        "remaining": float(tier.gmv_threshold - current_gmv),
                        "progress": progress,
                        "icon": tier.icon,
                        "color": tier.color
                    })
            
            # Sort by remaining GMV and return limited results
            upcoming.sort(key=lambda x: x["remaining"])
            return upcoming[:limit]
            
        except Exception as e:
            logger.error(f"Error getting next milestones: {str(e)}")
            raise
    
    async def calculate_completion_percentage(self, creator_id: UUID) -> float:
        """
        Calculate overall badge completion percentage
        
        Args:
            creator_id: UUID of the creator
            
        Returns:
            Percentage of all badges earned
        """
        try:
            result = await self.session.execute(
                select(func.count(CreatorBadge.id))
                .where(CreatorBadge.creator_id == creator_id)
            )
            earned_count = result.scalar() or 0
            
            total_badges = len(BADGE_TIERS)
            if total_badges == 0:
                return 0.0
            
            return (earned_count / total_badges) * 100
            
        except Exception as e:
            logger.error(f"Error calculating completion: {str(e)}")
            return 0.0