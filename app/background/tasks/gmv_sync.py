"""
GMV Sync Background Task
Synchronizes GMV data from TikTok Shop API
"""

import asyncio
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select, and_, or_
from sqlalchemy import update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_maker
from app.models.user import User, UserRole
from app.services.integrations.tiktok_shop_service import TikTokShopService
from app.services.badge_service import GMVCalculator
from app.utils.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


async def sync_creator_gmv(creator_id: UUID) -> Optional[Dict[str, Any]]:
    """
    Sync GMV data for a single creator
    
    Args:
        creator_id: UUID of the creator
        
    Returns:
        Sync result dictionary or None if failed
    """
    async with async_session_maker() as session:
        try:
            # Get creator's TikTok user ID
            result = await session.execute(
                select(User.tiktok_user_id, User.current_gmv)
                .where(User.id == creator_id)
            )
            row = result.one_or_none()
            
            if not row or not row[0]:
                logger.warning(f"Creator {creator_id} has no TikTok user ID")
                return None
            
            tiktok_user_id = row[0]
            previous_gmv = row[1] or Decimal(0)
            
            # Initialize TikTok service
            tiktok_service = TikTokShopService()
            
            if not tiktok_service.is_configured():
                logger.warning("TikTok Shop API not configured, using mock data")
            
            # Fetch GMV data
            gmv_data = await tiktok_service.get_creator_gmv(tiktok_user_id)
            
            if not gmv_data:
                logger.error(f"Failed to fetch GMV for creator {creator_id}")
                return None
            
            new_gmv = Decimal(str(gmv_data.get('total_gmv', 0)))
            
            # Update creator's GMV if changed
            if new_gmv != previous_gmv:
                await session.execute(
                    sql_update(User)
                    .where(User.id == creator_id)
                    .values(
                        current_gmv=new_gmv,
                        updated_at=datetime.utcnow()
                    )
                )
                await session.commit()
                
                logger.info(
                    f"Updated GMV for creator {creator_id}: "
                    f"{previous_gmv} -> {new_gmv}"
                )
                
                # Check for new badges if GMV increased
                if new_gmv > previous_gmv:
                    from app.background.tasks.badge_checker import check_creator_badges
                    new_badges = await check_creator_badges(creator_id)
                    
                    return {
                        "creator_id": str(creator_id),
                        "previous_gmv": float(previous_gmv),
                        "new_gmv": float(new_gmv),
                        "change": float(new_gmv - previous_gmv),
                        "new_badges": new_badges,
                        "timestamp": datetime.utcnow()
                    }
            
            return {
                "creator_id": str(creator_id),
                "gmv": float(new_gmv),
                "unchanged": True,
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error syncing GMV for creator {creator_id}: {str(e)}")
            return None


async def sync_all_creators_gmv(
    batch_size: int = 50,
    only_active: bool = True
) -> Dict[str, Any]:
    """
    Sync GMV data for all creators
    
    Args:
        batch_size: Number of creators to process concurrently
        only_active: Only sync active creators
        
    Returns:
        Summary of sync operation
    """
    async with async_session_maker() as session:
        try:
            start_time = datetime.utcnow()
            total_synced = 0
            total_updated = 0
            total_errors = 0
            total_gmv_change = Decimal(0)
            
            # Build query
            query = select(User.id).where(
                and_(
                    User.role == UserRole.CREATOR,
                    User.tiktok_user_id.isnot(None)
                )
            )
            
            if only_active:
                query = query.where(User.is_active == True)
            
            # Get all creator IDs
            result = await session.execute(query)
            creator_ids = [row[0] for row in result.all()]
            
            logger.info(f"Starting GMV sync for {len(creator_ids)} creators")
            
            # Process in batches
            for i in range(0, len(creator_ids), batch_size):
                batch_ids = creator_ids[i:i + batch_size]
                
                # Process batch concurrently
                tasks = [sync_creator_gmv(creator_id) for creator_id in batch_ids]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for result in results:
                    if isinstance(result, Exception):
                        total_errors += 1
                        logger.error(f"Sync error: {str(result)}")
                    elif result:
                        total_synced += 1
                        if not result.get('unchanged'):
                            total_updated += 1
                            change = result.get('change', 0)
                            total_gmv_change += Decimal(str(change))
                    else:
                        total_errors += 1
                
                # Log progress
                logger.info(
                    f"Progress: {total_synced + total_errors}/{len(creator_ids)} "
                    f"(Updated: {total_updated}, Errors: {total_errors})"
                )
                
                # Rate limiting
                await asyncio.sleep(2)
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                "execution_time_seconds": execution_time,
                "total_creators": len(creator_ids),
                "total_synced": total_synced,
                "total_updated": total_updated,
                "total_errors": total_errors,
                "total_gmv_change": float(total_gmv_change),
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error in GMV sync: {str(e)}")
            raise


async def sync_recent_campaign_participants(
    campaign_id: Optional[UUID] = None,
    days_back: int = 7
) -> Dict[str, Any]:
    """
    Sync GMV for creators who recently participated in campaigns
    
    Args:
        campaign_id: Specific campaign ID to sync (optional)
        days_back: Sync participants from last N days
        
    Returns:
        Summary of sync operation
    """
    async with async_session_maker() as session:
        try:
            # This would query campaign participants
            # For now, we'll use recently active creators as a proxy
            since_date = datetime.utcnow() - timedelta(days=days_back)
            
            query = (
                select(User.id)
                .where(
                    and_(
                        User.role == UserRole.CREATOR,
                        User.tiktok_user_id.isnot(None),
                        User.last_login >= since_date
                    )
                )
            )
            
            result = await session.execute(query)
            creator_ids = [row[0] for row in result.all()]
            
            logger.info(f"Syncing GMV for {len(creator_ids)} recent participants")
            
            # Process all at once if small batch
            tasks = [sync_creator_gmv(creator_id) for creator_id in creator_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count results
            synced = sum(1 for r in results if r and not isinstance(r, Exception))
            updated = sum(
                1 for r in results 
                if r and not isinstance(r, Exception) and not r.get('unchanged')
            )
            
            return {
                "creators_synced": synced,
                "creators_updated": updated,
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error syncing campaign participants: {str(e)}")
            raise


async def calculate_gmv_trends() -> Dict[str, Any]:
    """
    Calculate GMV trends across the network
    
    Returns:
        GMV trend analysis
    """
    async with async_session_maker() as session:
        try:
            gmv_calculator = GMVCalculator(session)
            
            # Get all active creators
            result = await session.execute(
                select(User.id, User.current_gmv)
                .where(
                    and_(
                        User.role == UserRole.CREATOR,
                        User.is_active == True,
                        User.current_gmv > 0
                    )
                )
            )
            
            creators = result.all()
            total_gmv = sum(row[1] for row in creators if row[1])
            
            # Calculate growth rates for sample of creators
            growth_rates = []
            sample_size = min(100, len(creators))
            
            for creator_id, _ in creators[:sample_size]:
                growth_rate = await gmv_calculator.get_gmv_growth_rate(
                    creator_id, 
                    days=30
                )
                if growth_rate != 0:
                    growth_rates.append(growth_rate)
            
            avg_growth_rate = sum(growth_rates) / len(growth_rates) if growth_rates else 0
            
            return {
                "total_network_gmv": float(total_gmv),
                "active_creators_with_gmv": len(creators),
                "average_growth_rate_30d": avg_growth_rate,
                "growth_rates_sample_size": len(growth_rates),
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error calculating GMV trends: {str(e)}")
            raise


# Scheduled task functions
async def scheduled_hourly_gmv_sync():
    """Hourly task to sync GMV for recently active creators"""
    logger.info("Starting scheduled hourly GMV sync")
    return await sync_recent_campaign_participants(days_back=1)


async def scheduled_daily_full_sync():
    """Daily task to sync GMV for all creators"""
    logger.info("Starting scheduled daily full GMV sync")
    return await sync_all_creators_gmv()


async def scheduled_weekly_trend_analysis():
    """Weekly task to analyze GMV trends"""
    logger.info("Starting scheduled weekly GMV trend analysis")
    return await calculate_gmv_trends()