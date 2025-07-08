"""
Demographics Sync Background Task (Optional)
Syncs demographics data from TikTok API when available
Currently operates in mock mode until API access is granted
"""

import asyncio
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timedelta
import random

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_maker
from app.models.user import User, UserRole
from app.schemas.creator import AudienceDemographicCreate, AudienceDemographicsBulkUpdate
from app.services.demographics import DemographicsService
from app.utils.demographics_constants import VALID_AGE_GROUPS, VALID_GENDERS, TIKTOK_PRIMARY_MARKETS
from app.utils.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class DemographicsSyncService:
    """Service for syncing demographics from external sources"""
    
    def __init__(self):
        self.sync_enabled = getattr(settings, 'DEMOGRAPHICS_SYNC_ENABLED', False)
        self.sync_interval_hours = getattr(settings, 'DEMOGRAPHICS_SYNC_INTERVAL_HOURS', 24)
        self.batch_size = getattr(settings, 'DEMOGRAPHICS_SYNC_BATCH_SIZE', 50)
        self.mock_mode = getattr(settings, 'DEMOGRAPHICS_MOCK_MODE', True)
    
    async def sync_creator_demographics(self, creator_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Sync demographics for a single creator
        
        Args:
            creator_id: UUID of the creator
            
        Returns:
            Sync result or None if failed
        """
        async with async_session_maker() as session:
            try:
                # Get creator's TikTok user ID
                result = await session.execute(
                    select(User.tiktok_user_id, User.username)
                    .where(User.id == creator_id)
                )
                row = result.one_or_none()
                
                if not row or not row[0]:
                    logger.warning(f"Creator {creator_id} has no TikTok user ID")
                    return None
                
                tiktok_user_id = row[0]
                username = row[1]
                
                # Get demographics from API (or mock)
                if self.mock_mode:
                    demographics_data = self._generate_mock_demographics(tiktok_user_id)
                else:
                    demographics_data = await self._fetch_from_tiktok_api(tiktok_user_id)
                
                if not demographics_data:
                    logger.error(f"Failed to fetch demographics for {username}")
                    return None
                
                # Convert to our schema
                demographics = self._convert_to_schema(demographics_data)
                
                # Update in database
                demographics_service = DemographicsService(session)
                bulk_update = AudienceDemographicsBulkUpdate(demographics=demographics)
                
                await demographics_service.update_demographics_bulk(
                    creator_id,
                    bulk_update
                )
                
                logger.info(f"Successfully synced demographics for {username}")
                
                return {
                    "creator_id": creator_id,
                    "username": username,
                    "demographics_count": len(demographics),
                    "synced_at": datetime.utcnow()
                }
                
            except Exception as e:
                logger.error(f"Error syncing demographics for {creator_id}: {str(e)}")
                return None
    
    async def sync_all_creators(self) -> Dict[str, Any]:
        """
        Sync demographics for all creators
        
        Returns:
            Summary of sync operation
        """
        logger.info("Starting demographics sync for all creators")
        
        success_count = 0
        error_count = 0
        skipped_count = 0
        
        async with async_session_maker() as session:
            # Get all creators who need sync
            result = await session.execute(
                select(User.id, User.username)
                .where(
                    User.role == UserRole.creator,
                    User.tiktok_user_id.isnot(None)
                )
            )
            creators = result.all()
            
            total_creators = len(creators)
            logger.info(f"Found {total_creators} creators to sync")
            
            # Process in batches
            for i in range(0, total_creators, self.batch_size):
                batch = creators[i:i + self.batch_size]
                
                # Process batch concurrently
                tasks = [
                    self.sync_creator_demographics(creator_id)
                    for creator_id, _ in batch
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Count results
                for result in results:
                    if isinstance(result, Exception):
                        error_count += 1
                    elif result is None:
                        skipped_count += 1
                    else:
                        success_count += 1
                
                # Rate limiting
                if i + self.batch_size < total_creators:
                    await asyncio.sleep(1)  # 1 second between batches
        
        summary = {
            "total_creators": total_creators,
            "success_count": success_count,
            "error_count": error_count,
            "skipped_count": skipped_count,
            "completed_at": datetime.utcnow()
        }
        
        logger.info(f"Demographics sync completed: {summary}")
        return summary
    
    async def sync_recently_active_creators(self, hours: int = 24) -> Dict[str, Any]:
        """
        Sync demographics for recently active creators only
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Summary of sync operation
        """
        since = datetime.utcnow() - timedelta(hours=hours)
        
        async with async_session_maker() as session:
            # Get recently active creators
            result = await session.execute(
                select(User.id)
                .where(
                    User.role == UserRole.creator,
                    User.tiktok_user_id.isnot(None),
                    User.last_login >= since
                )
            )
            creator_ids = [row[0] for row in result]
            
            logger.info(f"Found {len(creator_ids)} recently active creators")
            
            # Sync each creator
            success_count = 0
            for creator_id in creator_ids:
                result = await self.sync_creator_demographics(creator_id)
                if result:
                    success_count += 1
            
            return {
                "active_creators": len(creator_ids),
                "synced_count": success_count,
                "period_hours": hours,
                "completed_at": datetime.utcnow()
            }
    
    def _generate_mock_demographics(self, tiktok_user_id: str) -> Dict[str, Any]:
        """
        Generate realistic mock demographics data
        
        Args:
            tiktok_user_id: TikTok user ID (used as seed)
            
        Returns:
            Mock demographics data
        """
        # Use user ID as seed for consistency
        seed = hash(tiktok_user_id) % 10000
        random.seed(seed)
        
        # Generate gender distribution
        female_percentage = random.uniform(40, 80)
        male_percentage = 100 - female_percentage
        
        # Small chance of non-binary representation
        if random.random() < 0.1:
            non_binary = random.uniform(1, 5)
            female_percentage -= non_binary / 2
            male_percentage -= non_binary / 2
        else:
            non_binary = 0
        
        # Generate age distribution
        age_distributions = {
            "young_skewed": [5, 45, 30, 15, 5, 0],  # Young audience
            "balanced": [2, 25, 35, 25, 10, 3],      # Balanced
            "mature": [0, 15, 30, 30, 20, 5]        # Older audience
        }
        
        distribution_type = random.choice(list(age_distributions.keys()))
        age_percentages = age_distributions[distribution_type]
        
        # Add some randomness
        age_percentages = [
            max(0, p + random.uniform(-5, 5)) 
            for p in age_percentages
        ]
        
        # Normalize to 100%
        total = sum(age_percentages)
        age_percentages = [p / total * 100 for p in age_percentages]
        
        # Generate country distribution
        primary_country = random.choice(TIKTOK_PRIMARY_MARKETS[:10])
        countries = {
            primary_country: random.uniform(60, 85)
        }
        
        # Add secondary countries
        remaining = 100 - countries[primary_country]
        secondary_countries = random.sample(
            [c for c in TIKTOK_PRIMARY_MARKETS if c != primary_country],
            k=random.randint(2, 4)
        )
        
        for i, country in enumerate(secondary_countries):
            if i == len(secondary_countries) - 1:
                countries[country] = remaining
            else:
                share = random.uniform(5, remaining * 0.6)
                countries[country] = share
                remaining -= share
        
        # Build response
        demographics = {
            "gender_distribution": {
                "female": female_percentage,
                "male": male_percentage,
                "non_binary": non_binary
            },
            "age_distribution": dict(zip(VALID_AGE_GROUPS, age_percentages)),
            "country_distribution": countries,
            "last_updated": datetime.utcnow()
        }
        
        random.seed()  # Reset seed
        return demographics
    
    async def _fetch_from_tiktok_api(self, tiktok_user_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch demographics from TikTok API (placeholder)
        
        Args:
            tiktok_user_id: TikTok user ID
            
        Returns:
            Demographics data or None
        """
        # TODO: Implement when TikTok API access is available
        logger.warning("TikTok API not configured, using mock data")
        return self._generate_mock_demographics(tiktok_user_id)
    
    def _convert_to_schema(self, api_data: Dict[str, Any]) -> List[AudienceDemographicCreate]:
        """
        Convert API response to our schema format
        
        Args:
            api_data: Raw API response
            
        Returns:
            List of demographic entries
        """
        demographics = []
        
        gender_dist = api_data.get("gender_distribution", {})
        age_dist = api_data.get("age_distribution", {})
        country_dist = api_data.get("country_distribution", {})
        
        # Create entries for each combination
        for gender, gender_pct in gender_dist.items():
            if gender_pct <= 0:
                continue
            
            for age_group, age_pct in age_dist.items():
                if age_pct <= 0:
                    continue
                
                # Calculate combined percentage
                combined_pct = (gender_pct / 100) * (age_pct / 100) * 100
                
                # Distribute across countries
                for country, country_pct in country_dist.items():
                    final_pct = combined_pct * (country_pct / 100)
                    
                    if final_pct >= 0.1:  # Only include if meaningful
                        demographics.append(
                            AudienceDemographicCreate(
                                age_group=age_group,
                                gender=gender,
                                percentage=round(final_pct, 2),
                                country=country
                            )
                        )
        
        return demographics


# Scheduled task functions
async def scheduled_daily_sync():
    """Daily task to sync all creator demographics"""
    logger.info("Starting scheduled daily demographics sync")
    
    sync_service = DemographicsSyncService()
    if not sync_service.sync_enabled:
        logger.info("Demographics sync is disabled")
        return
    
    return await sync_service.sync_all_creators()


async def scheduled_hourly_sync():
    """Hourly task to sync recently active creators"""
    logger.info("Starting scheduled hourly demographics sync")
    
    sync_service = DemographicsSyncService()
    if not sync_service.sync_enabled:
        logger.info("Demographics sync is disabled")
        return
    
    return await sync_service.sync_recently_active_creators(hours=1)


# Manual trigger functions
async def sync_single_creator(creator_id: UUID):
    """Manually sync a single creator's demographics"""
    sync_service = DemographicsSyncService()
    return await sync_service.sync_creator_demographics(creator_id)


async def sync_creator_batch(creator_ids: List[UUID]):
    """Manually sync a batch of creators"""
    sync_service = DemographicsSyncService()
    
    results = []
    for creator_id in creator_ids:
        result = await sync_service.sync_creator_demographics(creator_id)
        results.append(result)
    
    return {
        "total": len(creator_ids),
        "success": len([r for r in results if r is not None]),
        "failed": len([r for r in results if r is None])
    }