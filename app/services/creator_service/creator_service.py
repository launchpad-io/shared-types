"""
Creator service for TikTok Shop Creator CRM
Handles creator-specific operations including demographics, performance tracking,
and public profile management.
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from decimal import Decimal
from collections import defaultdict

from sqlalchemy import select, delete, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

from app.models.user import User, UserRole
from app.models.creator import (
    CreatorAudienceDemographic, 
    CreatorBadge,
    AgeGroup,
    BadgeType
)
from app.schemas.creator import (
    AudienceDemographicCreate,
    DemographicsVisualizationData,
    DemographicSegment
)
from app.utils.logging import get_logger
from app.core.cache import cache

logger = get_logger(__name__)


class CreatorService:
    """Service for managing creator-specific operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_creator_by_id(self, creator_id: UUID) -> Optional[User]:
        """
        Get creator user with all relationships loaded.
        
        Args:
            creator_id: UUID of the creator
            
        Returns:
            User object if found and is creator, None otherwise
        """
        try:
            result = await self.session.execute(
                select(User)
                .options(
                    selectinload(User.badges),
                    selectinload(User.audience_demographics)
                )
                .where(
                    and_(
                        User.id == creator_id,
                        User.role == UserRole.creator
                    )
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching creator {creator_id}: {str(e)}")
            raise
    
    async def get_audience_demographics(
        self, 
        creator_id: UUID
    ) -> List[CreatorAudienceDemographic]:
        """
        Get all audience demographics for a creator.
        
        Args:
            creator_id: UUID of the creator
            
        Returns:
            List of demographic entries
        """
        try:
            result = await self.session.execute(
                select(CreatorAudienceDemographic)
                .where(CreatorAudienceDemographic.creator_id == creator_id)
                .order_by(
                    CreatorAudienceDemographic.gender,
                    CreatorAudienceDemographic.age_group
                )
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error fetching demographics for {creator_id}: {str(e)}")
            raise
    
    async def update_audience_demographics(
        self,
        creator_id: UUID,
        demographics: List[AudienceDemographicCreate]
    ) -> List[CreatorAudienceDemographic]:
        """
        Update all audience demographics for a creator.
        Replaces existing demographics with new data.
        
        Args:
            creator_id: UUID of the creator
            demographics: List of demographic data
            
        Returns:
            List of updated demographic entries
            
        Raises:
            ValueError: If demographics don't sum to 100% per gender
        """
        try:
            # Validate demographics sum to 100% per gender
            self._validate_demographics(demographics)
            
            # Delete existing demographics
            await self.session.execute(
                delete(CreatorAudienceDemographic)
                .where(CreatorAudienceDemographic.creator_id == creator_id)
            )
            
            # Create new demographics
            new_demographics = []
            for demo_data in demographics:
                demo = CreatorAudienceDemographic(
                    creator_id=creator_id,
                    age_group=demo_data.age_group,
                    gender=demo_data.gender,
                    percentage=demo_data.percentage,
                    country=demo_data.country
                )
                self.session.add(demo)
                new_demographics.append(demo)
            
            await self.session.commit()
            
            # Clear cache
            await self._clear_creator_cache(creator_id)
            
            logger.info(f"Updated {len(new_demographics)} demographics for creator {creator_id}")
            return new_demographics
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error updating demographics: {str(e)}")
            await self.session.rollback()
            raise
    
    async def add_demographic_entry(
        self,
        creator_id: UUID,
        demographic: AudienceDemographicCreate
    ) -> CreatorAudienceDemographic:
        """
        Add or update a single demographic entry.
        
        Args:
            creator_id: UUID of the creator
            demographic: Demographic data
            
        Returns:
            Created or updated demographic entry
        """
        try:
            # Check if entry exists
            result = await self.session.execute(
                select(CreatorAudienceDemographic)
                .where(
                    and_(
                        CreatorAudienceDemographic.creator_id == creator_id,
                        CreatorAudienceDemographic.age_group == demographic.age_group,
                        CreatorAudienceDemographic.gender == demographic.gender,
                        CreatorAudienceDemographic.country == demographic.country
                    )
                )
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                # Update existing
                existing.percentage = demographic.percentage
                existing.updated_at = datetime.utcnow()
                demo = existing
            else:
                # Create new
                demo = CreatorAudienceDemographic(
                    creator_id=creator_id,
                    age_group=demographic.age_group,
                    gender=demographic.gender,
                    percentage=demographic.percentage,
                    country=demographic.country
                )
                self.session.add(demo)
            
            await self.session.commit()
            await self._clear_creator_cache(creator_id)
            
            return demo
            
        except Exception as e:
            logger.error(f"Error adding demographic entry: {str(e)}")
            await self.session.rollback()
            raise
    
    # NEW: Enhanced demographics methods
    async def get_demographics_visualization_data(
        self, 
        creator_id: UUID
    ) -> DemographicsVisualizationData:
        """
        Get demographics data formatted for visualization.
        
        Args:
            creator_id: UUID of the creator
            
        Returns:
            Formatted data for charts
        """
        try:
            demographics = await self.get_audience_demographics(creator_id)
            
            if not demographics:
                # Return empty visualization data
                return DemographicsVisualizationData(
                    gender_distribution=[],
                    age_distribution=[],
                    location_distribution=[],
                    combined_segments=[],
                    summary_stats={
                        "total_segments": 0,
                        "has_demographics": False
                    }
                )
            
            # Gender distribution
            gender_data = defaultdict(float)
            for demo in demographics:
                gender_data[demo.gender] += float(demo.percentage)
            
            gender_distribution = [
                DemographicSegment(
                    label=self._format_gender_label(gender),
                    value=percentage,
                    color=self._get_gender_color(gender)
                )
                for gender, percentage in gender_data.items()
            ]
            
            # Age distribution
            age_data = defaultdict(float)
            for demo in demographics:
                age_data[demo.age_group] += float(demo.percentage)
            
            age_distribution = [
                DemographicSegment(
                    label=age_group,
                    value=percentage,
                    color=self._get_age_color(age_group)
                )
                for age_group, percentage in sorted(age_data.items())
            ]
            
            # Location distribution
            location_data = defaultdict(float)
            for demo in demographics:
                if demo.country:
                    location_data[demo.country] += float(demo.percentage)
            
            location_distribution = [
                DemographicSegment(
                    label=self._get_country_name(country),
                    value=percentage,
                    metadata={"code": country}
                )
                for country, percentage in sorted(
                    location_data.items(), 
                    key=lambda x: x[1], 
                    reverse=True
                )[:10]  # Top 10 countries
            ]
            
            # Combined segments (top 10)
            combined_segments = []
            for demo in sorted(demographics, key=lambda d: d.percentage, reverse=True)[:10]:
                combined_segments.append(
                    DemographicSegment(
                        label=f"{self._format_gender_label(demo.gender)} {demo.age_group}",
                        value=float(demo.percentage),
                        metadata={
                            "gender": demo.gender,
                            "age_group": demo.age_group,
                            "country": demo.country
                        }
                    )
                )
            
            # Summary stats
            primary_demo = max(demographics, key=lambda d: d.percentage)
            summary_stats = {
                "total_segments": len(demographics),
                "has_demographics": True,
                "primary_audience": {
                    "gender": primary_demo.gender,
                    "age_group": primary_demo.age_group,
                    "percentage": float(primary_demo.percentage)
                },
                "gender_balance": {
                    "female": gender_data.get("female", 0),
                    "male": gender_data.get("male", 0)
                }
            }
            
            return DemographicsVisualizationData(
                gender_distribution=gender_distribution,
                age_distribution=age_distribution,
                location_distribution=location_distribution,
                combined_segments=combined_segments,
                summary_stats=summary_stats
            )
            
        except Exception as e:
            logger.error(f"Error getting visualization data: {str(e)}")
            raise
    
    async def calculate_demographics_completeness(
        self, 
        creator_id: UUID
    ) -> float:
        """
        Calculate how complete the demographics data is.
        
        Args:
            creator_id: UUID of the creator
            
        Returns:
            Completeness percentage (0-100)
        """
        try:
            demographics = await self.get_audience_demographics(creator_id)
            
            if not demographics:
                return 0.0
            
            # Check for required combinations
            required_genders = {"male", "female"}
            required_age_groups = {"18-24", "25-34", "35-44"}
            
            present_genders = set(d.gender for d in demographics)
            present_age_groups = set(d.age_group for d in demographics)
            has_countries = any(d.country for d in demographics)
            
            # Calculate score
            score = 0.0
            
            # Gender coverage (40%)
            gender_coverage = len(present_genders.intersection(required_genders)) / len(required_genders)
            score += gender_coverage * 40
            
            # Age group coverage (40%)
            age_coverage = len(present_age_groups.intersection(required_age_groups)) / len(required_age_groups)
            score += age_coverage * 40
            
            # Country data (20%)
            if has_countries:
                score += 20
            
            return min(score, 100.0)
            
        except Exception as e:
            logger.error(f"Error calculating completeness: {str(e)}")
            return 0.0
    
    # EXISTING methods remain unchanged
    async def get_public_profile(self, creator_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get public-facing creator profile information.
        
        Args:
            creator_id: UUID of the creator
            
        Returns:
            Public profile data or None if not found
        """
        try:
            # Try to get from cache first
            cache_key = f"creator_public_profile:{creator_id}"
            cached = await cache.get(cache_key)
            if cached:
                return cached
            
            # Get creator data
            creator = await self.get_creator_by_id(creator_id)
            if not creator:
                return None
            
            # Get badge count
            badge_count = len(creator.badges) if creator.badges else 0
            
            # Get top badge
            top_badge = None
            if creator.badges:
                # Sort by GMV threshold to get highest badge
                sorted_badges = sorted(
                    creator.badges,
                    key=lambda b: b.gmv_threshold or 0,
                    reverse=True
                )
                if sorted_badges:
                    top_badge = {
                        'type': sorted_badges[0].badge_type,
                        'name': sorted_badges[0].badge_name
                    }
            
            # Build public profile
            profile = {
                'id': str(creator.id),
                'username': creator.username,
                'full_name': f"{creator.first_name or ''} {creator.last_name or ''}".strip() or None,
                'profile_image_url': creator.profile_image_url,
                'bio': creator.bio,
                'content_niche': creator.content_niche,
                'follower_count': creator.follower_count,
                'engagement_rate': float(creator.engagement_rate) if creator.engagement_rate else 0,
                'badges_earned': badge_count,
                'top_badge': top_badge,
                'member_since': creator.created_at.isoformat(),
                'social_media': {
                    'tiktok': creator.tiktok_handle,
                    'instagram': creator.instagram_handle
                }
            }
            
            # Cache for 1 hour
            await cache.set(cache_key, profile, expire=3600)
            
            return profile
            
        except Exception as e:
            logger.error(f"Error fetching public profile: {str(e)}")
            return None
    
    async def search_creators(
        self,
        search_term: Optional[str] = None,
        content_niche: Optional[str] = None,
        min_followers: Optional[int] = None,
        max_followers: Optional[int] = None,
        has_badges: Optional[bool] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """
        Search and filter creators.
        
        Args:
            search_term: Search in username, name, bio
            content_niche: Filter by content niche
            min_followers: Minimum follower count
            max_followers: Maximum follower count
            has_badges: Filter by badge presence
            page: Page number
            per_page: Items per page
            
        Returns:
            Paginated search results
        """
        try:
            # Build base query
            query = select(User).where(User.role == UserRole.creator)
            
            # Apply filters
            filters = []
            
            if search_term:
                search_pattern = f"%{search_term}%"
                filters.append(
                    or_(
                        User.username.ilike(search_pattern),
                        User.first_name.ilike(search_pattern),
                        User.last_name.ilike(search_pattern),
                        User.bio.ilike(search_pattern)
                    )
                )
            
            if content_niche:
                filters.append(User.content_niche == content_niche)
            
            if min_followers is not None:
                filters.append(User.follower_count >= min_followers)
            
            if max_followers is not None:
                filters.append(User.follower_count <= max_followers)
            
            if has_badges is not None:
                if has_badges:
                    # Has at least one badge
                    query = query.join(User.badges).distinct()
                else:
                    # No badges
                    query = query.outerjoin(User.badges).where(
                        CreatorBadge.id.is_(None)
                    )
            
            if filters:
                query = query.where(and_(*filters))
            
            # Count total
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await self.session.execute(count_query)
            total = total_result.scalar() or 0
            
            # Apply pagination
            offset = (page - 1) * per_page
            query = query.offset(offset).limit(per_page)
            
            # Order by follower count
            query = query.order_by(desc(User.follower_count))
            
            # Execute query
            result = await self.session.execute(query)
            creators = result.scalars().all()
            
            # Build response
            return {
                'creators': [
                    await self.get_public_profile(creator.id)
                    for creator in creators
                ],
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': (total + per_page - 1) // per_page
            }
            
        except Exception as e:
            logger.error(f"Error searching creators: {str(e)}")
            raise
    
    async def get_creator_stats(self, creator_id: UUID) -> Dict[str, Any]:
        """
        Get creator statistics summary.
        
        Args:
            creator_id: UUID of the creator
            
        Returns:
            Statistics dictionary
        """
        try:
            creator = await self.get_creator_by_id(creator_id)
            if not creator:
                raise ValueError("Creator not found")
            
            # Get demographic summary
            demographics = await self.get_audience_demographics(creator_id)
            
            # Calculate audience gender split
            gender_split = {'male': 0, 'female': 0, 'other': 0}
            for demo in demographics:
                if demo.gender == 'male':
                    gender_split['male'] += float(demo.percentage)
                elif demo.gender == 'female':
                    gender_split['female'] += float(demo.percentage)
                else:
                    gender_split['other'] += float(demo.percentage)
            
            # Get most common age group
            age_groups = {}
            for demo in demographics:
                age_groups[demo.age_group] = age_groups.get(demo.age_group, 0) + float(demo.percentage)
            
            top_age_group = max(age_groups.items(), key=lambda x: x[1])[0] if age_groups else None
            
            return {
                'total_followers': creator.follower_count or 0,
                'average_views': creator.average_views or 0,
                'engagement_rate': float(creator.engagement_rate) if creator.engagement_rate else 0,
                'content_niche': creator.content_niche,
                'badges_earned': len(creator.badges) if creator.badges else 0,
                'profile_completion': creator.profile_completion_percentage,
                'audience_gender_split': gender_split,
                'top_age_group': top_age_group,
                'member_since_days': (datetime.utcnow() - creator.created_at).days
            }
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error getting creator stats: {str(e)}")
            raise
    
    # Helper methods
    def _validate_demographics(self, demographics: List[AudienceDemographicCreate]) -> None:
        """Validate that demographics sum to 100% per gender"""
        gender_totals = {}
        
        for demo in demographics:
            gender = demo.gender
            percentage = float(demo.percentage)
            gender_totals[gender] = gender_totals.get(gender, 0) + percentage
        
        # Check each gender sums to approximately 100%
        for gender, total in gender_totals.items():
            if abs(total - 100.0) > 0.1:  # Allow 0.1% tolerance
                raise ValueError(
                    f"Demographics for gender '{gender}' must sum to 100% "
                    f"(current: {total}%)"
                )
    
    async def _clear_creator_cache(self, creator_id: UUID) -> None:
        """Clear all cache entries for a creator"""
        cache_keys = [
            f"creator_public_profile:{creator_id}",
            f"creator_stats:{creator_id}",
            f"creator_badges:{creator_id}",
            f"creator_demographics:{creator_id}"
        ]
        
        for key in cache_keys:
            await cache.delete(key)
    
    def _format_gender_label(self, gender: str) -> str:
        """Format gender for display"""
        labels = {
            'male': 'Male',
            'female': 'Female',
            'non_binary': 'Non-Binary',
            'prefer_not_to_say': 'Not Specified'
        }
        return labels.get(gender, gender.title())
    
    def _get_gender_color(self, gender: str) -> str:
        """Get color for gender visualization"""
        colors = {
            'male': '#3B82F6',      # Blue
            'female': '#EC4899',    # Pink
            'non_binary': '#8B5CF6', # Purple
            'prefer_not_to_say': '#6B7280'  # Gray
        }
        return colors.get(gender, '#6B7280')
    
    def _get_age_color(self, age_group: str) -> str:
        """Get color for age group visualization"""
        colors = {
            '13-17': '#F59E0B',    # Amber
            '18-24': '#3B82F6',    # Blue
            '25-34': '#10B981',    # Green
            '35-44': '#8B5CF6',    # Purple
            '45-54': '#EF4444',    # Red
            '55+': '#6B7280'       # Gray
        }
        return colors.get(age_group, '#6B7280')
    
    def _get_country_name(self, country_code: str) -> str:
        """Get country name from code"""
        # Common country mappings
        country_names = {
            'US': 'United States',
            'GB': 'United Kingdom',
            'CA': 'Canada',
            'AU': 'Australia',
            'DE': 'Germany',
            'FR': 'France',
            'JP': 'Japan',
            'CN': 'China',
            'IN': 'India',
            'BR': 'Brazil',
            'MX': 'Mexico'
        }
        return country_names.get(country_code, country_code)