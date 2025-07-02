"""
TikTok Shop Integration Service
Handles communication with TikTok Shop Partner Center API
"""

import os
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from decimal import Decimal
import httpx
from httpx import AsyncClient

from app.core.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class TikTokShopService:
    """Service for integrating with TikTok Shop API"""
    
    def __init__(self):
        self.api_key = os.getenv("TIKTOK_SHOP_API_KEY", "")
        self.api_secret = os.getenv("TIKTOK_SHOP_API_SECRET", "")
        self.app_id = os.getenv("TIKTOK_SHOP_APP_ID", "")
        self.shop_id = os.getenv("TIKTOK_SHOP_SHOP_ID", "")
        self.base_url = "https://open-api.tiktokglobalshop.com"
        self.mock_mode = not all([self.api_key, self.api_secret, self.app_id])
        
        if self.mock_mode:
            logger.warning("TikTok Shop API credentials not found. Running in mock mode.")
    
    def is_configured(self) -> bool:
        """Check if TikTok Shop API is properly configured"""
        return not self.mock_mode
    
    async def get_creator_gmv(self, tiktok_user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get total GMV for a creator
        
        Args:
            tiktok_user_id: TikTok user ID of the creator
            
        Returns:
            GMV data dictionary or None
        """
        try:
            if self.mock_mode:
                return self._get_mock_gmv_data(tiktok_user_id)
            
            # Real API implementation
            async with AsyncClient() as client:
                headers = self._get_headers()
                params = {
                    "creator_id": tiktok_user_id,
                    "shop_id": self.shop_id
                }
                
                response = await client.get(
                    f"{self.base_url}/api/v1/creator/gmv",
                    headers=headers,
                    params=params,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "total_gmv": data.get("total_gmv", 0),
                        "currency": data.get("currency", "USD"),
                        "last_updated": datetime.utcnow()
                    }
                else:
                    logger.error(f"TikTok API error: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching GMV from TikTok: {str(e)}")
            return None
    
    async def get_creator_gmv_by_period(
        self, 
        tiktok_user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Optional[Dict[str, Any]]:
        """
        Get GMV for a creator within a specific period
        
        Args:
            tiktok_user_id: TikTok user ID
            start_date: Period start date
            end_date: Period end date
            
        Returns:
            Period GMV data or None
        """
        try:
            if self.mock_mode:
                return self._get_mock_period_gmv(tiktok_user_id, start_date, end_date)
            
            async with AsyncClient() as client:
                headers = self._get_headers()
                params = {
                    "creator_id": tiktok_user_id,
                    "shop_id": self.shop_id,
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d")
                }
                
                response = await client.get(
                    f"{self.base_url}/api/v1/creator/gmv/period",
                    headers=headers,
                    params=params,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "period_gmv": data.get("gmv", 0),
                        "order_count": data.get("order_count", 0),
                        "start_date": start_date,
                        "end_date": end_date
                    }
                else:
                    logger.error(f"TikTok API error: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching period GMV: {str(e)}")
            return None
    
    async def get_detailed_gmv_breakdown(
        self, 
        tiktok_user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed GMV breakdown by various dimensions
        
        Args:
            tiktok_user_id: TikTok user ID
            
        Returns:
            Detailed GMV breakdown or None
        """
        try:
            if self.mock_mode:
                return self._get_mock_detailed_breakdown(tiktok_user_id)
            
            async with AsyncClient() as client:
                headers = self._get_headers()
                params = {
                    "creator_id": tiktok_user_id,
                    "shop_id": self.shop_id
                }
                
                response = await client.get(
                    f"{self.base_url}/api/v1/creator/gmv/breakdown",
                    headers=headers,
                    params=params,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"TikTok API error: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching GMV breakdown: {str(e)}")
            return None
    
    def _get_headers(self) -> Dict[str, str]:
        """Get API request headers with authentication"""
        # In real implementation, this would include proper OAuth signing
        return {
            "App-Key": self.app_id,
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def _get_mock_gmv_data(self, tiktok_user_id: str) -> Dict[str, Any]:
        """Get mock GMV data for testing"""
        # Generate consistent mock data based on user ID
        seed = hash(tiktok_user_id) % 1000
        base_gmv = 500 + (seed * 50)
        
        return {
            "total_gmv": base_gmv,
            "currency": "USD",
            "last_updated": datetime.utcnow()
        }
    
    def _get_mock_period_gmv(
        self, 
        tiktok_user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get mock period GMV data"""
        days = (end_date - start_date).days
        seed = hash(tiktok_user_id) % 100
        daily_avg = 10 + seed
        
        return {
            "period_gmv": daily_avg * days,
            "order_count": days * 2,
            "start_date": start_date,
            "end_date": end_date
        }
    
    def _get_mock_detailed_breakdown(self, tiktok_user_id: str) -> Dict[str, Any]:
        """Get mock detailed breakdown"""
        seed = hash(tiktok_user_id) % 1000
        total = 500 + (seed * 50)
        
        return {
            "total_gmv": float(total),
            "by_campaign": {
                "campaign_1": float(total * 0.4),
                "campaign_2": float(total * 0.35),
                "campaign_3": float(total * 0.25)
            },
            "by_month": {
                "2024-12": float(total * 0.3),
                "2024-11": float(total * 0.25),
                "2024-10": float(total * 0.2),
                "2024-09": float(total * 0.15),
                "2024-08": float(total * 0.1)
            },
            "by_product_category": {
                "Beauty": float(total * 0.4),
                "Fashion": float(total * 0.3),
                "Home": float(total * 0.2),
                "Electronics": float(total * 0.1)
            }
        }