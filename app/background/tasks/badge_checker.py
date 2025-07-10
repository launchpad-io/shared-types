"""
Badge Checker Background Task
Periodically checks and assigns badges based on GMV thresholds
"""

import asyncio
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import async_session_maker
from app.models.user import User, UserRole
from app.models.creator import CreatorBadge
from app.services.badge_service import BadgeService, GMVCalculator
# from app.services.notification_service.badge_notification_service import BadgeNotificationService
from app.utils.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


async def check_creator_badges(creator_id: UUID) -> List[str]:
    """
    Check and assign badges for a single creator
    
    Args:
        creator_id: UUID of the creator
        
    Returns:
        List of newly assigned badge types
    """
    async with async_session_maker() as session:
        try:
            # Initialize services
            badge_service = BadgeService(session)
            gmv_calculator = GMVCalculator(session)
            
            # Calculate current GMV
            logger.info(f"Calculating GMV for creator {creator_id}")
            current_gmv = await gmv_calculator.calculate_total_gmv(creator_id)
            
            # Check and assign badges
            new_badges = await badge_service.check_and_assign_badges(creator_id, current_gmv)
            
            if new_badges:
                logger.info(f"Assigned {len(new_badges)} new badges to creator {creator_id}")
                
                # Send notifications for new badges
                # TODO: Uncomment when notification service is implemented
                # try:
                #     notification_service = BadgeNotificationService(session)
                #     for badge in new_badges:
                #         await notification_service.send_badge_earned_notification(
                #             creator_id,
                #             badge.badge_type,
                #             badge.badge_name
                #         )
                # except Exception as e:
                #     logger.error(f"Failed to send badge notifications: {str(e)}")
                
                return [badge.badge_type for badge in new_badges]
            
            return []
            
        except Exception as e:
            logger.error(f"Error checking badges for creator {creator_id}: {str(e)}")
            return []


async def check_all_creators_badges(
    batch_size: int = 100,
    only_active: bool = True
) -> dict:
    """
    Check badges for all creators in batches
    
    Args:
        batch_size: Number of creators to process at once
        only_active: Only check active creators
        
    Returns:
        Summary of badge assignments
    """
    async with async_session_maker() as session:
        try:
            start_time = datetime.utcnow()
            total_processed = 0
            total_badges_assigned = 0
            badges_by_type = {}
            
            # Build query
            query = select(User.id).where(User.role == UserRole.CREATOR)
            
            if only_active:
                query = query.where(User.is_active == True)
            
            # Get all creator IDs
            result = await session.execute(query)
            creator_ids = [row[0] for row in result.all()]
            
            logger.info(f"Starting badge check for {len(creator_ids)} creators")
            
            # Process in batches
            for i in range(0, len(creator_ids), batch_size):
                batch_ids = creator_ids[i:i + batch_size]
                
                # Process batch concurrently
                tasks = [check_creator_badges(creator_id) for creator_id in batch_ids]
                results = await asyncio.gather(*tasks)
                
                # Count results
                for badge_types in results:
                    total_processed += 1
                    total_badges_assigned += len(badge_types)
                    
                    for badge_type in badge_types:
                        badges_by_type[badge_type] = badges_by_type.get(badge_type, 0) + 1
                
                # Log progress
                logger.info(f"Processed {total_processed}/{len(creator_ids)} creators")
                
                # Small delay between batches to avoid overload
                await asyncio.sleep(1)
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            summary = {
                "execution_time_seconds": execution_time,
                "total_creators_processed": total_processed,
                "total_badges_assigned": total_badges_assigned,
                "badges_by_type": badges_by_type,
                "timestamp": datetime.utcnow()
            }
            
            logger.info(f"Badge check completed: {summary}")
            return summary
            
        except Exception as e:
            logger.error(f"Error in batch badge check: {str(e)}")
            raise


async def check_recently_active_creators(hours: int = 24) -> dict:
    """
    Check badges only for creators who were recently active
    
    Args:
        hours: Check creators active in the last N hours
        
    Returns:
        Summary of badge assignments
    """
    async with async_session_maker() as session:
        try:
            since_time = datetime.utcnow() - timedelta(hours=hours)
            
            # Get recently active creators
            query = (
                select(User.id)
                .where(
                    and_(
                        User.role == UserRole.CREATOR,
                        User.is_active == True,
                        User.last_login >= since_time
                    )
                )
            )
            
            result = await session.execute(query)
            creator_ids = [row[0] for row in result.all()]
            
            logger.info(f"Found {len(creator_ids)} recently active creators")
            
            # Process all at once if small batch
            if len(creator_ids) <= 50:
                tasks = [check_creator_badges(creator_id) for creator_id in creator_ids]
                results = await asyncio.gather(*tasks)
                
                total_badges = sum(len(badges) for badges in results)
                
                return {
                    "creators_checked": len(creator_ids),
                    "badges_assigned": total_badges,
                    "timestamp": datetime.utcnow()
                }
            else:
                # Use batch processing for larger sets
                return await check_all_creators_badges(batch_size=50)
                
        except Exception as e:
            logger.error(f"Error checking recently active creators: {str(e)}")
            raise


async def verify_badge_integrity() -> dict:
    """
    Verify badge data integrity and fix any issues
    
    Returns:
        Summary of verification results
    """
    async with async_session_maker() as session:
        try:
            issues_found = 0
            issues_fixed = 0
            
            # Check for creators with GMV but missing badges
            query = (
                select(User)
                .options(selectinload(User.badges))
                .where(
                    and_(
                        User.role == UserRole.CREATOR,
                        User.current_gmv > 0
                    )
                )
            )
            
            result = await session.execute(query)
            creators = result.scalars().all()
            
            badge_service = BadgeService(session)
            
            for creator in creators:
                # Check if they should have badges based on GMV
                expected_badges = []
                from app.utils.badge_constants import BADGE_TIERS
                
                for tier in BADGE_TIERS:
                    if creator.current_gmv >= tier.gmv_threshold:
                        expected_badges.append(tier.badge_type)
                
                # Get actual badges
                actual_badges = {badge.badge_type for badge in creator.badges}
                
                # Find missing badges
                missing_badges = set(expected_badges) - actual_badges
                
                if missing_badges:
                    issues_found += len(missing_badges)
                    logger.warning(
                        f"Creator {creator.id} missing {len(missing_badges)} badges"
                    )
                    
                    # Fix by assigning missing badges
                    for badge_type in missing_badges:
                        try:
                            await badge_service.assign_badge(creator.id, badge_type)
                            issues_fixed += 1
                        except Exception as e:
                            logger.error(f"Failed to assign badge: {str(e)}")
            
            return {
                "issues_found": issues_found,
                "issues_fixed": issues_fixed,
                "creators_checked": len(creators),
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error verifying badge integrity: {str(e)}")
            raise


# Scheduled task functions for use with task schedulers like Celery or APScheduler
async def scheduled_daily_badge_check():
    """Daily task to check all creators for new badges"""
    logger.info("Starting scheduled daily badge check")
    return await check_all_creators_badges()


async def scheduled_hourly_active_check():
    """Hourly task to check recently active creators"""
    logger.info("Starting scheduled hourly active creator check")
    return await check_recently_active_creators(hours=1)


async def scheduled_weekly_integrity_check():
    """Weekly task to verify badge data integrity"""
    logger.info("Starting scheduled weekly integrity check")
    return await verify_badge_integrity()
