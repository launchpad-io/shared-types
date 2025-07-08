"""
Demographics Visualization Service
Prepares demographic data for charts and visualizations
"""

from typing import List, Dict, Any, Optional
from uuid import UUID
from decimal import Decimal
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.creator import CreatorAudienceDemographic, AgeGroup
from app.services.demographics.demographics_service import DemographicsService
from app.utils.logging import get_logger

logger = get_logger(__name__)


class DemographicsVisualizationService:
    """Service for preparing demographic data for visualizations"""
    
    # Define colors for consistent UI
    GENDER_COLORS = {
        'male': '#3B82F6',      # Blue
        'female': '#EC4899',    # Pink
        'non_binary': '#8B5CF6', # Purple
        'prefer_not_to_say': '#6B7280'  # Gray
    }
    
    AGE_COLORS = {
        '13-17': '#F59E0B',    # Amber
        '18-24': '#3B82F6',    # Blue
        '25-34': '#10B981',    # Green
        '35-44': '#8B5CF6',    # Purple
        '45-54': '#EF4444',    # Red
        '55+': '#6B7280'       # Gray
    }
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.demographics_service = DemographicsService(session)
    
    async def get_gender_distribution_chart_data(
        self,
        creator_id: UUID
    ) -> Dict[str, Any]:
        """
        Get gender distribution data formatted for pie/donut chart
        
        Returns:
            {
                "data": [
                    {"name": "Female", "value": 67.5, "color": "#EC4899"},
                    {"name": "Male", "value": 32.5, "color": "#3B82F6"}
                ],
                "total": 100.0,
                "summary": {
                    "primary_gender": "Female",
                    "primary_percentage": 67.5
                }
            }
        """
        demographics = await self.demographics_service.get_demographics(creator_id)
        
        if not demographics:
            return self._empty_gender_distribution()
        
        # Aggregate by gender
        gender_totals = defaultdict(Decimal)
        for demo in demographics:
            gender_totals[demo.gender] += demo.percentage
        
        # Format for chart
        data = []
        for gender, percentage in gender_totals.items():
            data.append({
                "name": self._format_gender_label(gender),
                "value": float(percentage),
                "color": self.GENDER_COLORS.get(gender, '#6B7280')
            })
        
        # Sort by value descending
        data.sort(key=lambda x: x['value'], reverse=True)
        
        # Calculate summary
        primary = data[0] if data else None
        
        return {
            "data": data,
            "total": float(sum(gender_totals.values())),
            "summary": {
                "primary_gender": primary['name'] if primary else None,
                "primary_percentage": primary['value'] if primary else 0
            }
        }
    
    async def get_age_distribution_chart_data(
        self,
        creator_id: UUID
    ) -> Dict[str, Any]:
        """
        Get age distribution data formatted for bar chart
        
        Returns:
            {
                "data": [
                    {"age_group": "18-24", "percentage": 45.0, "color": "#3B82F6"},
                    {"age_group": "25-34", "percentage": 35.0, "color": "#10B981"}
                ],
                "total": 100.0,
                "summary": {
                    "primary_age_group": "18-24",
                    "youth_percentage": 45.0,  # 13-24
                    "adult_percentage": 55.0   # 25+
                }
            }
        """
        demographics = await self.demographics_service.get_demographics(creator_id)
        
        if not demographics:
            return self._empty_age_distribution()
        
        # Aggregate by age group
        age_totals = defaultdict(Decimal)
        for demo in demographics:
            age_totals[demo.age_group] += demo.percentage
        
        # Format for chart with proper ordering
        age_order = ['13-17', '18-24', '25-34', '35-44', '45-54', '55+']
        data = []
        
        for age_group in age_order:
            if age_group in age_totals:
                data.append({
                    "age_group": age_group,
                    "percentage": float(age_totals[age_group]),
                    "color": self.AGE_COLORS.get(age_group, '#6B7280')
                })
        
        # Calculate summary metrics
        youth_percentage = float(
            age_totals.get('13-17', 0) + age_totals.get('18-24', 0)
        )
        adult_percentage = float(
            sum(age_totals.values()) - youth_percentage
        )
        
        primary_age = max(age_totals.items(), key=lambda x: x[1])[0] if age_totals else None
        
        return {
            "data": data,
            "total": float(sum(age_totals.values())),
            "summary": {
                "primary_age_group": primary_age,
                "youth_percentage": youth_percentage,
                "adult_percentage": adult_percentage
            }
        }
    
    async def get_location_distribution_data(
        self,
        creator_id: UUID,
        top_n: int = 10
    ) -> Dict[str, Any]:
        """
        Get location distribution data for map or list visualization
        
        Returns:
            {
                "data": [
                    {"country": "US", "country_name": "United States", "percentage": 78.5},
                    {"country": "CA", "country_name": "Canada", "percentage": 12.3}
                ],
                "total_countries": 5,
                "coverage_percentage": 90.8  # Top N countries coverage
            }
        """
        demographics = await self.demographics_service.get_demographics(creator_id)
        
        if not demographics:
            return self._empty_location_distribution()
        
        # Aggregate by country
        country_totals = defaultdict(Decimal)
        for demo in demographics:
            if demo.country:
                country_totals[demo.country] += demo.percentage
        
        # Sort by percentage
        sorted_countries = sorted(
            country_totals.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Format top N countries
        data = []
        coverage = Decimal(0)
        
        for i, (country, percentage) in enumerate(sorted_countries):
            if i < top_n:
                data.append({
                    "country": country,
                    "country_name": self._get_country_name(country),
                    "percentage": float(percentage)
                })
                coverage += percentage
        
        return {
            "data": data,
            "total_countries": len(country_totals),
            "coverage_percentage": float(coverage)
        }
    
    async def get_combined_demographics_data(
        self,
        creator_id: UUID
    ) -> Dict[str, Any]:
        """
        Get all demographic visualizations in one call
        
        Returns combined data for all chart types
        """
        gender_data = await self.get_gender_distribution_chart_data(creator_id)
        age_data = await self.get_age_distribution_chart_data(creator_id)
        location_data = await self.get_location_distribution_data(creator_id)
        
        # Get raw demographics for detailed breakdown
        demographics = await self.demographics_service.get_demographics(creator_id)
        
        # Create detailed breakdown
        breakdown = []
        for demo in demographics:
            breakdown.append({
                "segment": f"{self._format_gender_label(demo.gender)} {demo.age_group}",
                "country": demo.country or "Global",
                "percentage": float(demo.percentage),
                "gender": demo.gender,
                "age_group": demo.age_group
            })
        
        # Sort by percentage
        breakdown.sort(key=lambda x: x['percentage'], reverse=True)
        
        return {
            "gender_distribution": gender_data,
            "age_distribution": age_data,
            "location_distribution": location_data,
            "detailed_breakdown": breakdown[:20],  # Top 20 segments
            "has_demographics": len(demographics) > 0,
            "last_updated": demographics[0].updated_at if demographics else None
        }
    
    async def get_demographic_comparison_data(
        self,
        creator_ids: List[UUID]
    ) -> Dict[str, Any]:
        """
        Get demographic data for comparing multiple creators
        
        Args:
            creator_ids: List of creator UUIDs to compare
            
        Returns:
            Comparison data formatted for charts
        """
        if len(creator_ids) > 5:
            creator_ids = creator_ids[:5]  # Limit to 5 for readability
        
        comparison_data = {
            "creators": [],
            "gender_comparison": [],
            "age_comparison": [],
            "location_overlap": []
        }
        
        # Collect data for each creator
        all_demographics = {}
        for creator_id in creator_ids:
            demographics = await self.demographics_service.get_demographics(creator_id)
            all_demographics[creator_id] = demographics
        
        # Process gender comparison
        for creator_id in creator_ids:
            gender_data = await self.get_gender_distribution_chart_data(creator_id)
            
            creator_gender_data = {
                "creator_id": str(creator_id),
                "data": {}
            }
            
            for item in gender_data['data']:
                creator_gender_data['data'][item['name']] = item['value']
            
            comparison_data['gender_comparison'].append(creator_gender_data)
        
        # Process age comparison
        for creator_id in creator_ids:
            age_data = await self.get_age_distribution_chart_data(creator_id)
            
            creator_age_data = {
                "creator_id": str(creator_id),
                "data": {}
            }
            
            for item in age_data['data']:
                creator_age_data['data'][item['age_group']] = item['percentage']
            
            comparison_data['age_comparison'].append(creator_age_data)
        
        return comparison_data
    
    # Helper methods
    def _format_gender_label(self, gender: str) -> str:
        """Format gender for display"""
        labels = {
            'male': 'Male',
            'female': 'Female',
            'non_binary': 'Non-Binary',
            'prefer_not_to_say': 'Not Specified'
        }
        return labels.get(gender, gender.title())
    
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
            'MX': 'Mexico',
            'IT': 'Italy',
            'ES': 'Spain',
            'KR': 'South Korea',
            'NL': 'Netherlands',
            'SE': 'Sweden',
            'NO': 'Norway',
            'DK': 'Denmark',
            'FI': 'Finland',
            'PL': 'Poland'
        }
        return country_names.get(country_code, country_code)
    
    def _empty_gender_distribution(self) -> Dict[str, Any]:
        """Return empty gender distribution structure"""
        return {
            "data": [],
            "total": 0.0,
            "summary": {
                "primary_gender": None,
                "primary_percentage": 0
            }
        }
    
    def _empty_age_distribution(self) -> Dict[str, Any]:
        """Return empty age distribution structure"""
        return {
            "data": [],
            "total": 0.0,
            "summary": {
                "primary_age_group": None,
                "youth_percentage": 0.0,
                "adult_percentage": 0.0
            }
        }
    
    def _empty_location_distribution(self) -> Dict[str, Any]:
        """Return empty location distribution structure"""
        return {
            "data": [],
            "total_countries": 0,
            "coverage_percentage": 0.0
        }