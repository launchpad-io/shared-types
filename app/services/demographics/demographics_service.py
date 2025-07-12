# app/services/demographics_service.py
"""
Demographics service layer for business logic
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, delete
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
import uuid
from datetime import datetime, timedelta

from app.models.demographics import CreatorAudienceDemographics, GenderType
from app.schemas.demographics import DemographicsInsight

class DemographicsService:
    """Service class for demographics operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_creator_demographics(
        self, 
        creator_id: uuid.UUID
    ) -> List[CreatorAudienceDemographics]:
        """Get all demographics for a creator"""
        result = await self.db.execute(
            select(CreatorAudienceDemographics)
            .where(CreatorAudienceDemographics.creator_id == creator_id)
            .order_by(
                CreatorAudienceDemographics.age_group,
                CreatorAudienceDemographics.gender
            )
        )
        return result.scalars().all()
    
    async def validate_percentage_sum(
        self,
        creator_id: uuid.UUID,
        age_group: str,
        gender: GenderType,
        new_percentage: Decimal,
        exclude_id: Optional[uuid.UUID] = None
    ) -> Tuple[bool, Decimal]:
        """
        Validate that adding new percentage won't exceed 100%
        Returns: (is_valid, current_sum)
        """
        query = select(func.sum(CreatorAudienceDemographics.percentage)).where(
            and_(
                CreatorAudienceDemographics.creator_id == creator_id,
                CreatorAudienceDemographics.age_group == age_group,
                CreatorAudienceDemographics.gender == gender
            )
        )
        
        if exclude_id:
            query = query.where(CreatorAudienceDemographics.id != exclude_id)
        
        result = await self.db.execute(query)
        current_sum = result.scalar() or Decimal('0')
        
        is_valid = (current_sum + new_percentage) <= Decimal('100')
        return is_valid, current_sum
    
    async def get_top_demographics(
        self,
        creator_id: uuid.UUID,
        limit: int = 5
    ) -> List[CreatorAudienceDemographics]:
        """Get top demographics by percentage"""
        result = await self.db.execute(
            select(CreatorAudienceDemographics)
            .where(CreatorAudienceDemographics.creator_id == creator_id)
            .order_by(CreatorAudienceDemographics.percentage.desc())
            .limit(limit)
        )
        return result.scalars().all()
    
    async def get_demographics_by_country(
        self,
        creator_id: uuid.UUID,
        country: str
    ) -> List[CreatorAudienceDemographics]:
        """Get demographics filtered by country"""
        result = await self.db.execute(
            select(CreatorAudienceDemographics)
            .where(
                and_(
                    CreatorAudienceDemographics.creator_id == creator_id,
                    CreatorAudienceDemographics.country == country
                )
            )
        )
        return result.scalars().all()
    
    async def replace_all_demographics(
        self,
        creator_id: uuid.UUID,
        new_demographics: List[Dict]
    ) -> List[CreatorAudienceDemographics]:
        """Replace all demographics for a creator"""
        # Delete existing
        await self.db.execute(
            delete(CreatorAudienceDemographics)
            .where(CreatorAudienceDemographics.creator_id == creator_id)
        )
        
        # Create new
        created = []
        for demo_data in new_demographics:
            demo = CreatorAudienceDemographics(
                creator_id=creator_id,
                **demo_data
            )
            self.db.add(demo)
            created.append(demo)
        
        await self.db.flush()
        return created
    
    async def get_stale_demographics(
        self,
        days_old: int = 30
    ) -> List[Dict]:
        """Get creators with demographics older than specified days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        result = await self.db.execute(
            select(
                CreatorAudienceDemographics.creator_id,
                func.max(CreatorAudienceDemographics.updated_at).label('last_updated'),
                func.count(CreatorAudienceDemographics.id).label('entry_count')
            )
            .group_by(CreatorAudienceDemographics.creator_id)
            .having(func.max(CreatorAudienceDemographics.updated_at) < cutoff_date)
        )
        
        return [
            {
                'creator_id': str(row.creator_id),
                'last_updated': row.last_updated,
                'entry_count': row.entry_count
            }
            for row in result
        ]
    
    async def calculate_audience_overlap(
        self,
        creator_id1: uuid.UUID,
        creator_id2: uuid.UUID
    ) -> Dict[str, float]:
        """Calculate audience overlap between two creators"""
        # Get demographics for both creators
        demographics1 = await self.get_creator_demographics(creator_id1)
        demographics2 = await self.get_creator_demographics(creator_id2)
        
        # Create dictionaries for easy comparison
        demo1_dict = {
            (d.age_group, d.gender, d.country): d.percentage 
            for d in demographics1
        }
        demo2_dict = {
            (d.age_group, d.gender, d.country): d.percentage 
            for d in demographics2
        }
        
        # Calculate overlap
        overlap = Decimal('0')
        total_segments = set(demo1_dict.keys()) | set(demo2_dict.keys())
        
        for segment in total_segments:
            pct1 = demo1_dict.get(segment, Decimal('0'))
            pct2 = demo2_dict.get(segment, Decimal('0'))
            overlap += min(pct1, pct2)
        
        return {
            'overlap_percentage': float(overlap),
            'unique_segments_creator1': len(set(demo1_dict.keys()) - set(demo2_dict.keys())),
            'unique_segments_creator2': len(set(demo2_dict.keys()) - set(demo1_dict.keys())),
            'shared_segments': len(set(demo1_dict.keys()) & set(demo2_dict.keys()))
        }
    
    async def generate_demographics_insights(
        self,
        creator_id: uuid.UUID
    ) -> DemographicsInsight:
        """Generate insights about creator's demographics"""
        demographics = await self.get_creator_demographics(creator_id)
        
        if not demographics:
            raise ValueError("No demographics data available")
        
        # Find primary audience
        top_segment = max(demographics, key=lambda x: x.percentage)
        
        # Calculate concentration
        total_percentage = sum(d.percentage for d in demographics)
        avg_percentage = total_percentage / len(demographics) if demographics else 0
        variance = sum((d.percentage - avg_percentage) ** 2 for d in demographics) / len(demographics)
        concentration = float(variance ** 0.5)  # Standard deviation as concentration metric
        
        # Get top segments
        top_segments = sorted(demographics, key=lambda x: x.percentage, reverse=True)[:5]
        top_segments_data = [
            {
                'age_group': seg.age_group,
                'gender': seg.gender.value,
                'country': seg.country,
                'percentage': float(seg.percentage)
            }
            for seg in top_segments
        ]
        
        # Generate recommendations
        recommendations = []
        
        # Check for underrepresented age groups
        age_groups = {d.age_group for d in demographics}
        all_age_groups = {'13-17', '18-24', '25-34', '35-44', '45-54', '55+'}
        missing_age_groups = all_age_groups - age_groups
        if missing_age_groups:
            recommendations.append(f"Consider targeting age groups: {', '.join(missing_age_groups)}")
        
        # Check for gender balance
        gender_dist = {}
        for d in demographics:
            gender_dist[d.gender.value] = gender_dist.get(d.gender.value, 0) + float(d.percentage)
        
        if len(gender_dist) < 2:
            recommendations.append("Consider diversifying gender audience")
        
        # Check geographical diversity
        countries = {d.country for d in demographics if d.country}
        if len(countries) < 3:
            recommendations.append("Consider expanding to more geographical markets")
        
        return DemographicsInsight(
            creator_id=creator_id,
            primary_audience={
                'age_group': top_segment.age_group,
                'gender': top_segment.gender.value,
                'country': top_segment.country or 'Global'
            },
            audience_concentration=concentration,
            top_segments=top_segments_data,
            growth_segments=[],  # This would require historical data
            recommendations=recommendations
        )