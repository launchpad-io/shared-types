"""
API V1 Router
Combines all endpoint routers
"""

from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_active_user

# Import all endpoint routers
from app.api.v1.endpoints import (
    users, 
    creators, 
    badges,
)
from app.api.v1.endpoints.demographics import router as demographics_router

# Create main API router
api_router = APIRouter()

# Include routers we have implemented
api_router.include_router(
    users.router,
    prefix="/users",
    tags=["users"]
)

api_router.include_router(
    creators.router,
    prefix="/creators",
    tags=["creators"],
    dependencies=[Depends(get_current_active_user)]
)

api_router.include_router(
    badges.router,
    prefix="/badges",
    tags=["badges"],
    dependencies=[Depends(get_current_active_user)]
)

# NEW: Include demographics router
api_router.include_router(
    demographics_router,
    prefix="/demographics",
    tags=["demographics"],
    dependencies=[Depends(get_current_active_user)]
)

# API health check
@api_router.get("/", tags=["health"])
async def api_root():
    return {
        "message": "TikTok Shop Creator CRM API v1",
        "status": "operational",
        "documentation": "/docs",
        "version": "1.0.0"
    }

@api_router.get("/status", tags=["health"])
async def api_status():
    return {
        "status": "operational",
        "version": "1.0.0",
        "endpoints": {
            "users": "operational",
            "creators": "operational",
            "badges": "operational",
            "demographics": "operational",  # NEW
            # Add more as we implement them
            "auth": "not_implemented",
            "campaigns": "not_implemented",
            "applications": "not_implemented",
            "deliverables": "not_implemented",
            "payments": "not_implemented",
            "analytics": "not_implemented",
            "integrations": "not_implemented",
            "notifications": "not_implemented",
            "admin": "not_implemented"
        }
    }

# TODO: Add these routers as they are implemented:
# - auth router for authentication
# - campaigns router
# - applications router
# - deliverables router
# - payments router
# - analytics router
# - integrations router (for TikTok Shop, Discord, etc.)
# - notifications router
# - admin router