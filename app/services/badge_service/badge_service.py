"""
Badge Service
Core service for managing creator badges and achievements
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select, and_, or_, func
from sqlalchemy import update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.badge import CreatorBadge
from app.schemas.badge import (
    BadgeResponse,
    BadgeProgressResponse,
    BadgeHistoryResponse,
    BadgeStatsResponse
)
from app.utils.badge_constants import BADGE_TIERS, BadgeTier
from app.utils.logging import get_logger
# If exceptions module doesn't exist yet, we'll handle it gracefully
try:
    from app.core.exceptions import NotFoundException
except ImportError:
    # Fallback to HTTPException if custom exceptions not available
    from fastapi import HTTPException
    class NotFoundException(HTTPException):
        def __init__(self, detail: str = "Not found"):
            super().__init__(status_code=404, detail=detail)

logger = get_logger(__name__)


class BadgeService:
    """Service for managing creator badges and achievements"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_creator_badges(self, creator_id: UUID) -> List[BadgeResponse]:
        """
        Get all badges for a creator
        
        Args:
            creator_id: UUID of the creator
            
        Returns:
            List of badge responses
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
                raise NotFoundException(f"Creator {creator_id} not found")
            
            # Get earned badges
            earned_badges = {badge.badge_type: badge for badge in creator.badges}
            
            # Build response with all badge tiers
            badges = []
            for tier in BADGE_TIERS:
                if tier.badge_type in earned_badges:
                    badge = earned_badges[tier.badge_type]
                    status = "earned"
                    earned_date = badge.earned_at
                    progress = 100.0
                else:
                    status = self._get_badge_status(creator.current_gmv or Decimal(0), tier)
                    earned_date = None
                    progress = self._calculate_progress(creator.current_gmv or Decimal(0), tier)
                
                badges.append(BadgeResponse(
                    id=tier.badge_type,
                    badge_type=tier.badge_type,
                    name=tier.name,
                    description=tier.description,
                    tier=tier.tier,
                    gmv_requirement=float(tier.gmv_threshold),
                    status=status,
                    progress=progress,
                    earned_date=earned_date,
                    icon=tier.icon,
                    color=tier.color,
                    bg_color=tier.bg_color
                ))
            
            return badges
            
        except Exception as e:
            logger.error(f"Error fetching badges for creator {creator_id}: {str(e)}")
            raise
    
    async def assign_badge(self, creator_id: UUID, badge_type: str) -> CreatorBadge:
        """
        Assign a badge to a creator
        
        Args:
            creator_id: UUID of the creator
            badge_type: Type of badge to assign
            
        Returns:
            Created badge record
        """
        try:
            # Check if badge already exists
            existing = await self.session.execute(
                select(CreatorBadge)
                .where(
                    and_(
                        CreatorBadge.creator_id == creator_id,
                        CreatorBadge.badge_type == badge_type
                    )
                )
            )
            if existing.scalar_one_or_none():
                logger.info(f"Badge {badge_type} already assigned to creator {creator_id}")
                return existing.scalar_one()
            
            # Get badge tier info
            tier = next((t for t in BADGE_TIERS if t.badge_type == badge_type), None)
            if not tier:
                raise ValueError(f"Invalid badge type: {badge_type}")
            
            # Create new badge
            badge = CreatorBadge(
                creator_id=creator_id,
                badge_type=badge_type,
                badge_name=tier.name,
                badge_description=tier.description,
                gmv_threshold=tier.gmv_threshold,
                earned_at=datetime.utcnow(),
                is_active=True
            )
            
            self.session.add(badge)
            await self.session.commit()
            await self.session.refresh(badge)
            
            logger.info(f"Assigned badge {badge_type} to creator {creator_id}")
            
            # TODO: Trigger notification for badge achievement
            
            return badge
            
        except Exception as e:
            logger.error(f"Error assigning badge: {str(e)}")
            await self.session.rollback()
            raise
    
    async def check_and_assign_badges(self, creator_id: UUID, current_gmv: Decimal) -> List[CreatorBadge]:
        """
        Check GMV thresholds and assign any newly earned badges
        
        Args:
            creator_id: UUID of the creator
            current_gmv: Current GMV amount
            
        Returns:
            List of newly assigned badges
        """
        try:
            # Get existing badges
            result = await self.session.execute(
                select(CreatorBadge.badge_type)
                .where(CreatorBadge.creator_id == creator_id)
            )
            existing_types = {row[0] for row in result}
            
            # Check each tier
            new_badges = []
            for tier in BADGE_TIERS:
                if (tier.badge_type not in existing_types and 
                    current_gmv >= tier.gmv_threshold):
                    badge = await self.assign_badge(creator_id, tier.badge_type)
                    new_badges.append(badge)
            
            # Update creator's current GMV
            await self.session.execute(
                sql_update(User)
                .where(User.id == creator_id)
                .values(current_gmv=current_gmv)
            )
            await self.session.commit()
            
            return new_badges
            
        except Exception as e:
            logger.error(f"Error checking badges: {str(e)}")
            await self.session.rollback()
            raise
    
    async def get_badge_history(self, creator_id: UUID) -> List[BadgeHistoryResponse]:
        """
        Get badge achievement history for a creator
        
        Args:
            creator_id: UUID of the creator
            
        Returns:
            List of badge history entries
        """
        try:
            result = await self.session.execute(
                select(CreatorBadge)
                .where(CreatorBadge.creator_id == creator_id)
                .order_by(CreatorBadge.earned_at.desc())
            )
            badges = result.scalars().all()
            
            history = []
            for badge in badges:
                tier = next((t for t in BADGE_TIERS if t.badge_type == badge.badge_type), None)
                if tier:
                    history.append(BadgeHistoryResponse(
                        date=badge.earned_at,
                        badge_name=badge.badge_name,
                        badge_type=badge.badge_type,
                        gmv_at_time=float(badge.gmv_threshold),
                        message=f"Achieved {tier.name} status!",
                        icon=tier.icon,
                        color=tier.color
                    ))
            
            return history
            
        except Exception as e:
            logger.error(f"Error fetching badge history: {str(e)}")
            raise
    
    async def get_network_badge_stats(self) -> BadgeStatsResponse:
        """
        Get network-wide badge statistics
        
        Returns:
            Badge statistics across all creators
        """
        try:
            # Count badges by type
            result = await self.session.execute(
                select(
                    CreatorBadge.badge_type,
                    func.count(CreatorBadge.id).label('count')
                )
                .group_by(CreatorBadge.badge_type)
            )
            
            badge_counts = {row[0]: row[1] for row in result}
            
            # Get total creators
            total_creators = await self.session.execute(
                select(func.count(User.id))
                .where(User.role == 'creator')
            )
            total = total_creators.scalar() or 0
            
            # Build distribution
            distribution = {}
            for tier in BADGE_TIERS:
                count = badge_counts.get(tier.badge_type, 0)
                distribution[tier.badge_type] = {
                    "count": count,
                    "percentage": (count / total * 100) if total > 0 else 0,
                    "name": tier.name
                }
            
            return BadgeStatsResponse(
                total_badges_earned=sum(badge_counts.values()),
                creators_with_badges=len(set(badge_counts.keys())),
                badge_distribution=distribution
            )
            
        except Exception as e:
            logger.error(f"Error fetching badge stats: {str(e)}")
            raise
    
    def _get_badge_status(self, current_gmv: Decimal, tier: BadgeTier) -> str:
        """Determine badge status based on GMV"""
        if current_gmv >= tier.gmv_threshold:
            return "earned"
        elif current_gmv >= tier.gmv_threshold * Decimal(0.5):
            return "in-progress"
        else:
            return "locked"
    
    def _calculate_progress(self, current_gmv: Decimal, tier: BadgeTier) -> float:
        """Calculate progress percentage toward a badge"""
        if current_gmv >= tier.gmv_threshold:
            return 100.0
        return float(current_gmv / tier.gmv_threshold * 100)