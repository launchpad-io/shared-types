from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_active_user
from app.api.v1.endpoints import (
    auth,
    creators,
    campaigns,
    applications,
    deliverables,
    payments,
    analytics,
    integrations,
    notifications,
    admin
)

# Create main API router
api_router = APIRouter()

# Public routes (no authentication required)
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["authentication"]
)

# Protected routes (authentication required)
api_router.include_router(
    creators.router,
    prefix="/creators",
    tags=["creators"],
    dependencies=[Depends(get_current_active_user)]
)

api_router.include_router(
    campaigns.router,
    prefix="/campaigns",
    tags=["campaigns"],
    dependencies=[Depends(get_current_active_user)]
)

api_router.include_router(
    applications.router,
    prefix="/applications",
    tags=["applications"],
    dependencies=[Depends(get_current_active_user)]
)

api_router.include_router(
    deliverables.router,
    prefix="/deliverables",
    tags=["deliverables"],
    dependencies=[Depends(get_current_active_user)]
)

api_router.include_router(
    payments.router,
    prefix="/payments",
    tags=["payments"],
    dependencies=[Depends(get_current_active_user)]
)

api_router.include_router(
    analytics.router,
    prefix="/analytics",
    tags=["analytics"],
    dependencies=[Depends(get_current_active_user)]
)

api_router.include_router(
    integrations.router,
    prefix="/integrations",
    tags=["integrations"],
    dependencies=[Depends(get_current_active_user)]
)

api_router.include_router(
    notifications.router,
    prefix="/notifications",
    tags=["notifications"],
    dependencies=[Depends(get_current_active_user)]
)

# Admin routes (admin role required)
api_router.include_router(
    admin.router,
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_active_user)]
)

# API health check
@api_router.get("/", tags=["health"])
async def api_root():
    return {
        "message": "TikTok Shop Creator CRM API v1",
        "status": "operational",
        "documentation": "/docs"
    }

@api_router.get("/status", tags=["health"])
async def api_status():
    return {
        "status": "operational",
        "version": "1.0.0",
        "endpoints": {
            "auth": "operational",
            "creators": "operational",
            "campaigns": "operational",
            "applications": "operational",
            "deliverables": "operational",
            "payments": "operational",
            "analytics": "operational",
            "integrations": "operational",
            "notifications": "operational",
            "admin": "operational"
        }
    }