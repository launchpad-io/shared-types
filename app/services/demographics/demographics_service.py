"""
Core Demographics Service
Manages creator audience demographics CRUD operations
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.models.creator import CreatorAudienceDemographic, AgeGroup, GenderType
from app.models.user import User
from app.schemas.creator import (
    AudienceDemographicCreate,
    AudienceDemographicResponse,
    AudienceDemographicsBulkUpdate
)
from app.services.demographics.validator import DemographicsValidator
from app.core.cache import cache
from app.utils.logging import get_logger
from app.core.exceptions import (
    NotFoundException,
    ValidationException,
    BusinessLogicException
)

logger = get_logger(__name__)


class DemographicsService:
    """Service for managing creator audience demographics"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.validator = DemographicsValidator()
    
    async def get_demographics(self, creator_id: UUID) -> List[CreatorAudienceDemographic]:
        """
        Get all demographics for a creator
        
        Args:
            creator_id: UUID of the creator
            
        Returns:
            List of demographic entries
            
        Raises:
            NotFoundException: If creator not found
        """
        # Check if creator exists
        creator = await self._get_creator(creator_id)
        if not creator:
            raise NotFoundException(f"Creator {creator_id} not found")
        
        # Try cache first
        cache_key = f"demographics:{creator_id}"
        cached = await cache.get(cache_key)
        if cached:
            return cached
        
        # Query demographics
        result = await self.session.execute(
            select(CreatorAudienceDemographic)
            .where(CreatorAudienceDemographic.creator_id == creator_id)
            .order_by(
                CreatorAudienceDemographic.gender,
                CreatorAudienceDemographic.age_group
            )
        )
        demographics = result.scalars().all()
        
        # Cache for 5 minutes
        await cache.set(cache_key, demographics, expire=300)
        
        return demographics
    
    async def update_demographics_bulk(
        self,
        creator_id: UUID,
        demographics_data: AudienceDemographicsBulkUpdate
    ) -> List[CreatorAudienceDemographic]:
        """
        Bulk update all demographics for a creator
        Replaces existing data with new data
        
        Args:
            creator_id: UUID of the creator
            demographics_data: Bulk update data
            
        Returns:
            List of updated demographic entries
            
        Raises:
            ValidationException: If data validation fails
            NotFoundException: If creator not found
        """
        # Verify creator exists
        creator = await self._get_creator(creator_id)
        if not creator:
            raise NotFoundException(f"Creator {creator_id} not found")
        
        # Validate demographics
        validation_result = self.validator.validate_bulk_demographics(
            demographics_data.demographics
        )
        if not validation_result.is_valid:
            raise ValidationException(validation_result.errors)
        
        try:
            # Delete existing demographics in transaction
            await self.session.execute(
                delete(CreatorAudienceDemographic)
                .where(CreatorAudienceDemographic.creator_id == creator_id)
            )
            
            # Create new demographics
            new_demographics = []
            for demo_data in demographics_data.demographics:
                demographic = CreatorAudienceDemographic(
                    creator_id=creator_id,
                    age_group=demo_data.age_group,
                    gender=demo_data.gender,
                    percentage=Decimal(str(demo_data.percentage)),
                    country=demo_data.country
                )
                self.session.add(demographic)
                new_demographics.append(demographic)
            
            await self.session.commit()
            
            # Clear cache
            await self._clear_demographics_cache(creator_id)
            
            logger.info(f"Updated {len(new_demographics)} demographics for creator {creator_id}")
            return new_demographics
            
        except IntegrityError as e:
            await self.session.rollback()
            logger.error(f"Database integrity error: {str(e)}")
            raise BusinessLogicException("Failed to update demographics due to data conflict")
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error updating demographics: {str(e)}")
            raise
    
    async def add_or_update_demographic(
        self,
        creator_id: UUID,
        demographic_data: AudienceDemographicCreate
    ) -> CreatorAudienceDemographic:
        """
        Add or update a single demographic entry
        
        Args:
            creator_id: UUID of the creator
            demographic_data: Demographic data to add/update
            
        Returns:
            Created or updated demographic entry
        """
        # Verify creator exists
        creator = await self._get_creator(creator_id)
        if not creator:
            raise NotFoundException(f"Creator {creator_id} not found")
        
        try:
            # Check if entry exists
            result = await self.session.execute(
                select(CreatorAudienceDemographic)
                .where(
                    and_(
                        CreatorAudienceDemographic.creator_id == creator_id,
                        CreatorAudienceDemographic.age_group == demographic_data.age_group,
                        CreatorAudienceDemographic.gender == demographic_data.gender,
                        CreatorAudienceDemographic.country == (
                            demographic_data.country if demographic_data.country else None
                        )
                    )
                )
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                # Update existing
                existing.percentage = Decimal(str(demographic_data.percentage))
                existing.updated_at = datetime.utcnow()
                demographic = existing
            else:
                # Create new
                demographic = CreatorAudienceDemographic(
                    creator_id=creator_id,
                    age_group=demographic_data.age_group,
                    gender=demographic_data.gender,
                    percentage=Decimal(str(demographic_data.percentage)),
                    country=demographic_data.country
                )
                self.session.add(demographic)
            
            await self.session.commit()
            await self._clear_demographics_cache(creator_id)
            
            return demographic
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error adding/updating demographic: {str(e)}")
            raise
    
    async def delete_demographic(
        self,
        creator_id: UUID,
        demographic_id: UUID
    ) -> bool:
        """
        Delete a specific demographic entry
        
        Args:
            creator_id: UUID of the creator
            demographic_id: UUID of the demographic entry
            
        Returns:
            True if deleted, False if not found
        """
        result = await self.session.execute(
            delete(CreatorAudienceDemographic)
            .where(
                and_(
                    CreatorAudienceDemographic.id == demographic_id,
                    CreatorAudienceDemographic.creator_id == creator_id
                )
            )
        )
        
        if result.rowcount > 0:
            await self.session.commit()
            await self._clear_demographics_cache(creator_id)
            return True
        
        return False
    
    async def get_demographics_summary(self, creator_id: UUID) -> Dict[str, Any]:
        """
        Get summarized demographics data
        
        Args:
            creator_id: UUID of the creator
            
        Returns:
            Dictionary with demographic summaries
        """
        demographics = await self.get_demographics(creator_id)
        
        if not demographics:
            return {
                "has_demographics": False,
                "gender_distribution": {},
                "age_distribution": {},
                "top_countries": [],
                "primary_audience": None
            }
        
        # Calculate distributions
        gender_dist = {}
        age_dist = {}
        country_dist = {}
        
        for demo in demographics:
            # Gender distribution
            gender = demo.gender
            if gender not in gender_dist:
                gender_dist[gender] = Decimal(0)
            gender_dist[gender] += demo.percentage
            
            # Age distribution
            age = demo.age_group
            if age not in age_dist:
                age_dist[age] = Decimal(0)
            age_dist[age] += demo.percentage
            
            # Country distribution
            if demo.country:
                if demo.country not in country_dist:
                    country_dist[demo.country] = Decimal(0)
                country_dist[demo.country] += demo.percentage
        
        # Find primary audience
        primary_demo = max(demographics, key=lambda d: d.percentage)
        
        # Sort countries by percentage
        top_countries = sorted(
            [(c, float(p)) for c, p in country_dist.items()],
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return {
            "has_demographics": True,
            "gender_distribution": {k: float(v) for k, v in gender_dist.items()},
            "age_distribution": {k: float(v) for k, v in age_dist.items()},
            "top_countries": top_countries,
            "primary_audience": {
                "age_group": primary_demo.age_group,
                "gender": primary_demo.gender,
                "percentage": float(primary_demo.percentage)
            }
        }
    
    async def search_creators_by_demographics(
        self,
        filters: Dict[str, Any],
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Search creators by demographic criteria
        
        Args:
            filters: Search filters (age_groups, genders, countries, min_percentage)
            limit: Number of results
            offset: Pagination offset
            
        Returns:
            Dictionary with creators and pagination info
        """
        query = select(User).where(User.role == 'creator')
        
        # Apply demographic filters
        if any(filters.get(k) for k in ['age_groups', 'genders', 'countries']):
            subquery = select(CreatorAudienceDemographic.creator_id).distinct()
            
            if filters.get('age_groups'):
                subquery = subquery.where(
                    CreatorAudienceDemographic.age_group.in_(filters['age_groups'])
                )
            
            if filters.get('genders'):
                subquery = subquery.where(
                    CreatorAudienceDemographic.gender.in_(filters['genders'])
                )
            
            if filters.get('countries'):
                subquery = subquery.where(
                    CreatorAudienceDemographic.country.in_(filters['countries'])
                )
            
            if filters.get('min_percentage'):
                subquery = subquery.where(
                    CreatorAudienceDemographic.percentage >= filters['min_percentage']
                )
            
            query = query.where(User.id.in_(subquery))
        
        # Count total
        count_result = await self.session.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar() or 0
        
        # Apply pagination
        query = query.offset(offset).limit(limit)
        
        # Execute query
        result = await self.session.execute(query)
        creators = result.scalars().all()
        
        return {
            "creators": creators,
            "total": total,
            "limit": limit,
            "offset": offset,
            "pages": (total + limit - 1) // limit
        }
    
    # Helper methods
    async def _get_creator(self, creator_id: UUID) -> Optional[User]:
        """Get creator by ID"""
        result = await self.session.execute(
            select(User).where(
                and_(
                    User.id == creator_id,
                    User.role == 'creator'
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def _clear_demographics_cache(self, creator_id: UUID) -> None:
        """Clear demographics cache for a creator"""
        cache_keys = [
            f"demographics:{creator_id}",
            f"demographics_summary:{creator_id}",
            f"creator_profile:{creator_id}"
        ]
        for key in cache_keys:
            await cache.delete(key)