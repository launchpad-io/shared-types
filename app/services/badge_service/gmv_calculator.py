"""
GMV Calculator Service
Handles GMV aggregation and calculations from various sources
"""

from typing import Optional, Dict, List, Tuple, Any
from uuid import UUID
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select, func, and_, or_
from sqlalchemy import update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.utils.logging import get_logger
from app.services.integrations.tiktok_shop_service import TikTokShopService

logger = get_logger(__name__)


class GMVCalculator:
    """Service for calculating and aggregating GMV data"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.tiktok_service = TikTokShopService()
    
    async def calculate_total_gmv(self, creator_id: UUID) -> Decimal:
        """
        Calculate total lifetime GMV for a creator
        
        Args:
            creator_id: UUID of the creator
            
        Returns:
            Total GMV amount
        """
        try:
            # Try to get from TikTok Shop API
            if self.tiktok_service.is_configured():
                # Get creator's TikTok user ID
                result = await self.session.execute(
                    select(User.tiktok_user_id)
                    .where(User.id == creator_id)
                )
                tiktok_user_id = result.scalar_one_or_none()
                
                if tiktok_user_id:
                    gmv_data = await self.tiktok_service.get_creator_gmv(tiktok_user_id)
                    if gmv_data:
                        return Decimal(str(gmv_data.get('total_gmv', 0)))
            
            # Fallback to database calculation (from campaigns/deliverables)
            # This would aggregate from campaign_creators and deliverables tables
            # For now, return cached value
            result = await self.session.execute(
                select(User.current_gmv)
                .where(User.id == creator_id)
            )
            return result.scalar_one_or_none() or Decimal(0)
            
        except Exception as e:
            logger.error(f"Error calculating GMV for creator {creator_id}: {str(e)}")
            return Decimal(0)
    
    async def calculate_period_gmv(
        self, 
        creator_id: UUID, 
        start_date: datetime,
        end_date: Optional[datetime] = None
    ) -> Decimal:
        """
        Calculate GMV for a specific time period
        
        Args:
            creator_id: UUID of the creator
            start_date: Start of period
            end_date: End of period (defaults to now)
            
        Returns:
            GMV for the period
        """
        try:
            if not end_date:
                end_date = datetime.utcnow()
            
            if self.tiktok_service.is_configured():
                result = await self.session.execute(
                    select(User.tiktok_user_id)
                    .where(User.id == creator_id)
                )
                tiktok_user_id = result.scalar_one_or_none()
                
                if tiktok_user_id:
                    gmv_data = await self.tiktok_service.get_creator_gmv_by_period(
                        tiktok_user_id,
                        start_date,
                        end_date
                    )
                    if gmv_data:
                        return Decimal(str(gmv_data.get('period_gmv', 0)))
            
            # Fallback logic would go here
            return Decimal(0)
            
        except Exception as e:
            logger.error(f"Error calculating period GMV: {str(e)}")
            return Decimal(0)
    
    async def calculate_average_daily_gmv(
        self, 
        creator_id: UUID, 
        days: int = 30
    ) -> Decimal:
        """
        Calculate average daily GMV over specified days
        
        Args:
            creator_id: UUID of the creator
            days: Number of days to average over
            
        Returns:
            Average daily GMV
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            period_gmv = await self.calculate_period_gmv(creator_id, start_date)
            
            if period_gmv > 0:
                return period_gmv / Decimal(days)
            
            return Decimal(0)
            
        except Exception as e:
            logger.error(f"Error calculating average GMV: {str(e)}")
            return Decimal(0)
    
    async def get_gmv_breakdown(self, creator_id: UUID) -> Dict[str, Any]:
        """
        Get detailed GMV breakdown by source/campaign
        
        Args:
            creator_id: UUID of the creator
            
        Returns:
            Dictionary with GMV breakdown
        """
        try:
            breakdown = {
                "total_gmv": Decimal(0),
                "by_campaign": {},
                "by_month": {},
                "by_product_category": {}
            }
            
            if self.tiktok_service.is_configured():
                result = await self.session.execute(
                    select(User.tiktok_user_id)
                    .where(User.id == creator_id)
                )
                tiktok_user_id = result.scalar_one_or_none()
                
                if tiktok_user_id:
                    detailed_data = await self.tiktok_service.get_detailed_gmv_breakdown(
                        tiktok_user_id
                    )
                    if detailed_data:
                        return detailed_data
            
            # Fallback to database aggregation
            total_gmv = await self.calculate_total_gmv(creator_id)
            breakdown["total_gmv"] = float(total_gmv)
            
            return breakdown
            
        except Exception as e:
            logger.error(f"Error getting GMV breakdown: {str(e)}")
            return {"total_gmv": 0}
    
    async def bulk_update_gmv(self, creator_ids: List[UUID]) -> Dict[UUID, Decimal]:
        """
        Update GMV for multiple creators at once
        
        Args:
            creator_ids: List of creator UUIDs
            
        Returns:
            Dictionary mapping creator_id to updated GMV
        """
        try:
            updated = {}
            
            for creator_id in creator_ids:
                gmv = await self.calculate_total_gmv(creator_id)
                
                # Update in database
                await self.session.execute(
                    sql_update(User)
                    .where(User.id == creator_id)
                    .values(
                        current_gmv=gmv,
                        updated_at=datetime.utcnow()
                    )
                )
                
                updated[creator_id] = gmv
            
            await self.session.commit()
            logger.info(f"Updated GMV for {len(updated)} creators")
            
            return updated
            
        except Exception as e:
            logger.error(f"Error in bulk GMV update: {str(e)}")
            await self.session.rollback()
            raise
    
    async def get_gmv_growth_rate(
        self, 
        creator_id: UUID, 
        days: int = 30
    ) -> float:
        """
        Calculate GMV growth rate over specified period
        
        Args:
            creator_id: UUID of the creator
            days: Period to calculate growth over
            
        Returns:
            Growth rate as percentage
        """
        try:
            # Current period
            current_end = datetime.utcnow()
            current_start = current_end - timedelta(days=days)
            current_gmv = await self.calculate_period_gmv(
                creator_id, 
                current_start, 
                current_end
            )
            
            # Previous period
            previous_end = current_start
            previous_start = previous_end - timedelta(days=days)
            previous_gmv = await self.calculate_period_gmv(
                creator_id, 
                previous_start, 
                previous_end
            )
            
            if previous_gmv > 0:
                growth = ((current_gmv - previous_gmv) / previous_gmv) * 100
                return float(growth)
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error calculating growth rate: {str(e)}")
            return 0.0