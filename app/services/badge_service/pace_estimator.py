"""
Pace Estimator Service
Estimates time to achieve badges based on historical performance
"""

from typing import Optional, Dict, List, Tuple
from uuid import UUID
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.creator import CreatorBadge
from app.services.badge_service.gmv_calculator import GMVCalculator
from app.utils.badge_constants import BADGE_TIERS
from app.schemas.badge import PaceEstimateResponse
from app.utils.logging import get_logger

logger = get_logger(__name__)


class PaceEstimator:
    """Service for estimating badge achievement pace"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.gmv_calculator = GMVCalculator(session)
    
    async def estimate_time_to_badge(
        self, 
        creator_id: UUID, 
        badge_type: str,
        lookback_days: int = 30
    ) -> PaceEstimateResponse:
        """
        Estimate time to achieve a specific badge
        
        Args:
            creator_id: UUID of the creator
            badge_type: Type of badge to estimate for
            lookback_days: Days to look back for pace calculation
            
        Returns:
            Pace estimate response
        """
        try:
            # Get creator and badge info
            result = await self.session.execute(
                select(User)
                .where(User.id == creator_id)
            )
            creator = result.scalar_one_or_none()
            
            if not creator:
                raise ValueError(f"Creator {creator_id} not found")
            
            # Find badge tier
            tier = next((t for t in BADGE_TIERS if t.badge_type == badge_type), None)
            if not tier:
                raise ValueError(f"Invalid badge type: {badge_type}")
            
            current_gmv = creator.current_gmv or Decimal(0)
            
            # Check if already earned
            badge_check = await self.session.execute(
                select(CreatorBadge)
                .where(
                    and_(
                        CreatorBadge.creator_id == creator_id,
                        CreatorBadge.badge_type == badge_type
                    )
                )
            )
            if badge_check.scalar_one_or_none():
                return PaceEstimateResponse(
                    badge_type=badge_type,
                    badge_name=tier.name,
                    is_achieved=True,
                    current_gmv=float(current_gmv),
                    target_gmv=float(tier.gmv_threshold),
                    days_to_achieve=0,
                    estimated_date=None,
                    daily_average_needed=0.0,
                    current_daily_average=0.0,
                    confidence_level="achieved"
                )
            
            # Calculate average daily GMV
            avg_daily_gmv = await self.gmv_calculator.calculate_average_daily_gmv(
                creator_id, 
                lookback_days
            )
            
            # Calculate time to badge
            remaining_gmv = tier.gmv_threshold - current_gmv
            
            if avg_daily_gmv > 0:
                days_to_achieve = int(remaining_gmv / avg_daily_gmv)
                estimated_date = datetime.utcnow() + timedelta(days=days_to_achieve)
                confidence = self._calculate_confidence(creator_id, lookback_days)
            else:
                # No recent activity
                days_to_achieve = None
                estimated_date = None
                confidence = "no_data"
            
            # Calculate daily average needed for different timeframes
            daily_needed_30 = float(remaining_gmv / 30)
            daily_needed_60 = float(remaining_gmv / 60)
            daily_needed_90 = float(remaining_gmv / 90)
            
            return PaceEstimateResponse(
                badge_type=badge_type,
                badge_name=tier.name,
                is_achieved=False,
                current_gmv=float(current_gmv),
                target_gmv=float(tier.gmv_threshold),
                remaining_gmv=float(remaining_gmv),
                days_to_achieve=days_to_achieve,
                estimated_date=estimated_date,
                daily_average_needed=daily_needed_30,
                current_daily_average=float(avg_daily_gmv),
                confidence_level=confidence,
                pace_breakdown={
                    "30_days": daily_needed_30,
                    "60_days": daily_needed_60,
                    "90_days": daily_needed_90
                }
            )
            
        except Exception as e:
            logger.error(f"Error estimating badge pace: {str(e)}")
            raise
    
    async def estimate_all_badges(
        self, 
        creator_id: UUID,
        lookback_days: int = 30
    ) -> List[PaceEstimateResponse]:
        """
        Estimate time to achieve all unearned badges
        
        Args:
            creator_id: UUID of the creator
            lookback_days: Days to look back for pace calculation
            
        Returns:
            List of pace estimates for all badges
        """
        try:
            # Get earned badges
            result = await self.session.execute(
                select(CreatorBadge.badge_type)
                .where(CreatorBadge.creator_id == creator_id)
            )
            earned_types = {row[0] for row in result}
            
            estimates = []
            for tier in BADGE_TIERS:
                if tier.badge_type not in earned_types:
                    estimate = await self.estimate_time_to_badge(
                        creator_id,
                        tier.badge_type,
                        lookback_days
                    )
                    estimates.append(estimate)
            
            return estimates
            
        except Exception as e:
            logger.error(f"Error estimating all badges: {str(e)}")
            raise
    
    async def get_performance_trend(
        self, 
        creator_id: UUID,
        period_days: int = 90
    ) -> Dict[str, any]:
        """
        Get GMV performance trend over time
        
        Args:
            creator_id: UUID of the creator
            period_days: Number of days to analyze
            
        Returns:
            Performance trend data
        """
        try:
            # Calculate GMV for different periods
            periods = [7, 14, 30, 60, 90]
            trend_data = {
                "periods": [],
                "growth_rate": 0.0,
                "trend": "stable",
                "peak_day": None,
                "lowest_day": None
            }
            
            for days in periods:
                if days <= period_days:
                    avg_gmv = await self.gmv_calculator.calculate_average_daily_gmv(
                        creator_id,
                        days
                    )
                    trend_data["periods"].append({
                        "days": days,
                        "average_daily_gmv": float(avg_gmv),
                        "total_gmv": float(avg_gmv * days)
                    })
            
            # Calculate growth rate
            if len(trend_data["periods"]) >= 2:
                recent = trend_data["periods"][0]["average_daily_gmv"]
                older = trend_data["periods"][-1]["average_daily_gmv"]
                
                if older > 0:
                    growth = ((recent - older) / older) * 100
                    trend_data["growth_rate"] = growth
                    
                    if growth > 20:
                        trend_data["trend"] = "accelerating"
                    elif growth > 0:
                        trend_data["trend"] = "growing"
                    elif growth < -20:
                        trend_data["trend"] = "declining"
                    else:
                        trend_data["trend"] = "stable"
            
            return trend_data
            
        except Exception as e:
            logger.error(f"Error getting performance trend: {str(e)}")
            raise
    
    async def get_milestone_forecast(
        self, 
        creator_id: UUID
    ) -> List[Dict[str, any]]:
        """
        Forecast when each milestone will be achieved
        
        Args:
            creator_id: UUID of the creator
            
        Returns:
            List of milestone forecasts
        """
        try:
            forecasts = []
            
            # Get all estimates
            estimates = await self.estimate_all_badges(creator_id)
            
            for estimate in estimates:
                if not estimate.is_achieved and estimate.estimated_date:
                    forecasts.append({
                        "badge_type": estimate.badge_type,
                        "badge_name": estimate.badge_name,
                        "estimated_date": estimate.estimated_date,
                        "days_remaining": estimate.days_to_achieve,
                        "confidence": estimate.confidence_level,
                        "required_daily_gmv": estimate.daily_average_needed
                    })
            
            # Sort by estimated date
            forecasts.sort(key=lambda x: x["estimated_date"])
            
            return forecasts
            
        except Exception as e:
            logger.error(f"Error getting milestone forecast: {str(e)}")
            raise
    
    def _calculate_confidence(self, creator_id: UUID, lookback_days: int) -> str:
        """
        Calculate confidence level for pace estimates
        
        Args:
            creator_id: UUID of the creator
            lookback_days: Days used for calculation
            
        Returns:
            Confidence level string
        """
        # This would analyze consistency of GMV generation
        # For now, return based on lookback period
        if lookback_days >= 60:
            return "high"
        elif lookback_days >= 30:
            return "medium"
        else:
            return "low"
