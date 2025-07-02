"""
Badge service for managing creator achievements
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from decimal import Decimal
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.creator import CreatorBadge, BadgeType
from app.models.user import User
from app.utils.logging import get_logger

logger = get_logger(__name__)


class BadgeService:
    """Service for managing creator badges"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_creator_badges(self, creator_id: UUID) -> List[CreatorBadge]:
        """Get all badges earned by a creator"""
        result = await self.session.execute(
            select(CreatorBadge)
            .where(CreatorBadge.creator_id == creator_id)
            .order_by(CreatorBadge.earned_at)
        )
        return result.scalars().all()
    
    async def get_all_badges_progress(self, creator_id: UUID) -> Dict[str, Any]:
        """Get progress towards all badges"""
        # TODO: Implement actual GMV calculation
        current_gmv = Decimal("15000")  # Placeholder
        
        badges = await self.get_creator_badges(creator_id)
        earned_badges = {b.badge_type for b in badges}
        
        all_badge_progress = []
        badge_definitions = CreatorBadge.get_badge_definitions()
        
        for badge_type, definition in badge_definitions.items():
            progress = min(
                float(current_gmv / definition['threshold'] * 100), 
                100.0
            )
            
            all_badge_progress.append({
                'badge_type': badge_type,
                'badge_name': definition['name'],
                'description': definition['description'],
                'threshold': definition['threshold'],
                'color': definition['color'],
                'earned': badge_type in earned_badges,
                'earned_at': next(
                    (b.earned_at for b in badges if b.badge_type == badge_type), 
                    None
                ),
                'current_gmv': current_gmv,
                'progress_percentage': progress,
                'gmv_needed': max(definition['threshold'] - current_gmv, Decimal('0'))
            })
        
        # Find next badge
        unearned = [b for b in all_badge_progress if not b['earned']]
        next_badge = min(unearned, key=lambda x: x['threshold']) if unearned else None
        
        return {
            'total_gmv': current_gmv,
            'badges_earned': len(earned_badges),
            'badges_available': len(badge_definitions),
            'next_badge': next_badge,
            'all_badges': all_badge_progress
        }
    
    async def check_and_award_badges(
        self, 
        creator_id: UUID, 
        current_gmv: Decimal
    ) -> List[CreatorBadge]:
        """Check and award any newly earned badges"""
        # TODO: Implement badge awarding logic
        return []
    
    async def award_badge_manually(
        self, 
        creator_id: UUID, 
        badge_type: BadgeType,
        awarded_by: UUID
    ) -> CreatorBadge:
        """Manually award a badge (admin only)"""
        # TODO: Implement manual badge awarding
        pass