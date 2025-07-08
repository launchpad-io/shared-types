"""
API V1 Router
Combines all endpoint routers
"""
# app/api/v1/api.py

from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_active_user

# Import routers directly to avoid confusion
from app.api.v1.endpoints.users import router as users_router
from app.api.v1.endpoints.creators import router as creators_router
from app.api.v1.endpoints.badges import router as badges_router
from app.api.v1.endpoints.demographics import router as demographics_router

# Create main API router
api_router = APIRouter()

# Include routers without duplicate prefixes
# The users router already has internal routing, so no prefix needed
api_router.include_router(
    users_router,
    tags=["users"]
)

api_router.include_router(
    creators_router,
    prefix="/creators",
    tags=["creators"],
    dependencies=[Depends(get_current_active_user)]
)

api_router.include_router(
    badges_router,
    prefix="/badges",
    tags=["badges"],
    dependencies=[Depends(get_current_active_user)]
)

api_router.include_router(
    demographics_router,
    prefix="/demographics",
    tags=["demographics"],
    dependencies=[Depends(get_current_active_user)]
)

# API health check endpoints
@api_router.get("/", tags=["health"])
async def api_root():
    """API root endpoint with basic information"""
    return {
        "message": "TikTok Shop Creator CRM API v1",
        "status": "operational",
        "documentation": "/docs",
        "version": "1.0.0"
    }

@api_router.get("/status", tags=["health"])
async def api_status():
    """Detailed API status endpoint"""
    return {
        "status": "operational",
        "version": "1.0.0",
        "endpoints": {
            "users": "operational",
            "creators": "operational",
            "badges": "operational", 
            "demographics": "operational",
            # Mark unimplemented endpoints
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

# Future router imports (when implemented):
# from app.api.v1.endpoints.auth import router as auth_router
# from app.api.v1.endpoints.campaigns import router as campaigns_router
# from app.api.v1.endpoints.applications import router as applications_router
# from app.api.v1.endpoints.deliverables import router as deliverables_router
# from app.api.v1.endpoints.payments import router as payments_router
# from app.api.v1.endpoints.analytics import router as analytics_router
# from app.api.v1.endpoints.integrations import router as integrations_router
# from app.api.v1.endpoints.notifications import router as notifications_router
# from app.api.v1.endpoints.admin import router as admin_router