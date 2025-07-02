"""
Analytics service for creator performance metrics
"""

from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User, UserRole
from app.models.creator import CreatorAudienceDemographic, CreatorBadge
from app.schemas.creator import (
    DemographicsAnalytics,
    CreatorRankingResponse,
    CreatorAnalyticsSummary
)
from app.utils.logging import get_logger

logger = get_logger(__name__)


class CreatorAnalyticsService:
    """Service for creator analytics and performance metrics"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_performance_metrics(
        self, 
        creator_id: UUID, 
        time_period: str = "all_time"
    ) -> Dict[str, Any]:
        """Get creator performance metrics"""
        # TODO: Implement actual metrics calculation when order data is available
        return {
            'total_gmv': Decimal("125000.00"),
            'total_orders': 2500,
            'average_order_value': Decimal("50.00"),
            'conversion_rate': 3.5,
            'engagement_rate': 5.2,
            'total_campaigns': 15,
            'active_campaigns': 3,
            'completed_campaigns': 12,
            'average_campaign_gmv': Decimal("8333.33"),
            'best_performing_niche': "fashion",
            'performance_trend': "trending_up"
        }
    
    async def get_creator_leaderboard(
        self,
        period: str = "all-time",
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get creator leaderboard"""
        try:
            # Base query for creators
            query = select(User).where(User.role == UserRole.creator)
            
            # TODO: Add period filtering when order data is available
            # For now, order by current GMV
            query = query.order_by(User.current_gmv.desc().nullslast())
            
            # Count total
            count_result = await self.session.execute(
                select(func.count()).select_from(User).where(User.role == UserRole.creator)
            )
            total = count_result.scalar() or 0
            
            # Apply pagination
            query = query.offset(offset).limit(limit)
            
            # Load with badges
            query = query.options(selectinload(User.badges))
            
            # Execute
            result = await self.session.execute(query)
            creators = result.scalars().all()
            
            # Build leaderboard entries
            leaderboard = []
            for idx, creator in enumerate(creators, start=offset + 1):
                # Count badges
                earned_badges = [b for b in creator.badges if b.is_active]
                highest_badge = None
                if earned_badges:
                    sorted_badges = sorted(
                        earned_badges,
                        key=lambda b: b.gmv_threshold or 0,
                        reverse=True
                    )
                    highest_badge = sorted_badges[0].badge_name
                
                leaderboard.append(CreatorRankingResponse(
                    rank=idx,
                    creator_id=creator.id,
                    username=creator.username,
                    profile_image_url=creator.profile_image_url,
                    total_gmv=float(creator.current_gmv or 0),
                    badges_earned=len(earned_badges),
                    highest_badge=highest_badge,
                    content_niche=creator.content_niche,
                    follower_count=creator.follower_count,
                    change_in_rank=0  # TODO: Track historical rankings
                ))
            
            return {
                'total': total,
                'creators': leaderboard
            }
            
        except Exception as e:
            logger.error(f"Error getting leaderboard: {str(e)}")
            raise
    
    async def get_creator_ranking(self, creator_id: UUID) -> Dict[str, Any]:
        """Get specific creator's ranking"""
        # TODO: Implement actual ranking when more data is available
        return {
            'creator_id': creator_id,
            'username': 'creator123',
            'profile_image_url': None,
            'total_gmv': Decimal("15000.00"),
            'rank': 42,
            'percentile': 99.2,
            'movement': 5,
            'badges_earned': 3,
            'top_badge': 'gmv_10k'
        }
    
    # NEW: Demographics analytics methods
    async def get_demographics_analytics(
        self,
        creator_id: UUID,
        period_days: int = 30
    ) -> DemographicsAnalytics:
        """
        Get analytics for creator demographics.
        
        Args:
            creator_id: UUID of the creator
            period_days: Period for analytics
            
        Returns:
            Demographics analytics data
        """
        try:
            # Get creator and demographics
            result = await self.session.execute(
                select(User)
                .options(selectinload(User.audience_demographics))
                .where(User.id == creator_id)
            )
            creator = result.scalar_one_or_none()
            
            if not creator:
                raise ValueError("Creator not found")
            
            demographics = creator.audience_demographics
            
            # Calculate primary segments
            primary_gender = None
            primary_age = None
            primary_location = None
            
            if demographics:
                # Find highest percentage by category
                gender_max = max(demographics, key=lambda d: d.percentage)
                primary_gender = gender_max.gender
                
                age_groups = {}
                for demo in demographics:
                    age_groups[demo.age_group] = age_groups.get(demo.age_group, 0) + float(demo.percentage)
                if age_groups:
                    primary_age = max(age_groups.items(), key=lambda x: x[1])[0]
                
                location_groups = {}
                for demo in demographics:
                    if demo.country:
                        location_groups[demo.country] = location_groups.get(demo.country, 0) + float(demo.percentage)
                if location_groups:
                    primary_location = max(location_groups.items(), key=lambda x: x[1])[0]
            
            # Calculate engagement by demographic (mock data for now)
            engagement_by_demo = {
                "female_18-24": 5.8,
                "female_25-34": 4.2,
                "male_18-24": 3.9,
                "male_25-34": 3.5
            }
            
            # Calculate growth by demographic (mock data for now)
            growth_by_demo = {
                "female_18-24": 12.5,
                "female_25-34": 8.3,
                "male_18-24": 6.7,
                "male_25-34": 4.2
            }
            
            return DemographicsAnalytics(
                total_reach=creator.follower_count or 0,
                primary_gender=primary_gender,
                primary_age_group=primary_age,
                primary_location=primary_location,
                engagement_by_demographic=engagement_by_demo,
                growth_by_demographic=growth_by_demo
            )
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error getting demographics analytics: {str(e)}")
            raise
    
    async def get_analytics_summary(
        self,
        creator_id: UUID,
        start_date: datetime,
        end_date: datetime
    ) -> CreatorAnalyticsSummary:
        """
        Get comprehensive analytics summary for a period.
        
        Args:
            creator_id: UUID of the creator
            start_date: Start of period
            end_date: End of period
            
        Returns:
            Analytics summary
        """
        try:
            # Get creator
            result = await self.session.execute(
                select(User)
                .options(
                    selectinload(User.badges),
                    selectinload(User.audience_demographics)
                )
                .where(User.id == creator_id)
            )
            creator = result.scalar_one_or_none()
            
            if not creator:
                raise ValueError("Creator not found")
            
            # TODO: When order/campaign data is available, calculate real metrics
            # For now, return mock data
            
            period_days = (end_date - start_date).days
            
            return CreatorAnalyticsSummary(
                creator_id=creator_id,
                period_start=start_date,
                period_end=end_date,
                total_gmv=float(creator.current_gmv or 0),
                total_orders=int(float(creator.current_gmv or 0) / 50),  # Mock average order value
                average_order_value=50.0,
                conversion_rate=3.5,
                total_views=creator.average_views * period_days if creator.average_views else 0,
                total_clicks=int((creator.average_views or 0) * period_days * 0.05),  # 5% CTR
                engagement_rate=float(creator.engagement_rate) if creator.engagement_rate else 0,
                campaigns_participated=0,  # TODO: From campaigns
                campaigns_completed=0,  # TODO: From campaigns
                deliverables_submitted=0,  # TODO: From campaigns
                deliverables_approved=0,  # TODO: From campaigns
                gmv_growth=15.5,  # Mock growth
                follower_growth=8.3,  # Mock growth
                engagement_growth=2.1,  # Mock growth
                top_products=[],  # TODO: From order data
                top_campaigns=[]  # TODO: From campaign data
            )
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error getting analytics summary: {str(e)}")
            raise
    
    async def get_demographic_performance_correlation(
        self,
        creator_id: UUID
    ) -> Dict[str, Any]:
        """
        Analyze correlation between demographics and performance.
        
        Args:
            creator_id: UUID of the creator
            
        Returns:
            Correlation analysis data
        """
        try:
            # Get demographics
            result = await self.session.execute(
                select(CreatorAudienceDemographic)
                .where(CreatorAudienceDemographic.creator_id == creator_id)
            )
            demographics = result.scalars().all()
            
            if not demographics:
                return {
                    "has_data": False,
                    "correlations": {}
                }
            
            # TODO: When order data is available, calculate actual correlations
            # For now, return mock analysis
            
            correlations = {}
            for demo in demographics:
                segment_key = f"{demo.gender}_{demo.age_group}"
                correlations[segment_key] = {
                    "percentage": float(demo.percentage),
                    "avg_order_value": 50.0 + (float(demo.percentage) * 0.5),  # Mock correlation
                    "conversion_rate": 3.0 + (float(demo.percentage) * 0.02),  # Mock correlation
                    "engagement_rate": 4.0 + (float(demo.percentage) * 0.03)  # Mock correlation
                }
            
            return {
                "has_data": True,
                "correlations": correlations,
                "insights": [
                    "Female 18-24 segment shows highest engagement",
                    "Conversion rates are strongest in 25-34 age group",
                    "Consider targeting content for growing male audience"
                ]
            }
            
        except Exception as e:
            logger.error(f"Error analyzing demographic correlation: {str(e)}")
            return {
                "has_data": False,
                "correlations": {},
                "error": str(e)
            }