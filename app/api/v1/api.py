"""
API V1 Router
Combines all endpoint routers
"""
#app/api/v1/api.py
from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_active_user

# Import routers
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.users import router as users_router
from app.api.v1.endpoints.creators import router as creators_router
from app.api.v1.endpoints.badges import router as badges_router
from app.api.v1.endpoints.demographics import router as demographics_router

# Create main API router
api_router = APIRouter()

# Include auth router (no auth required for auth endpoints)
# api_router.include_router(
#     auth_router,
#     prefix="/auth",
#     tags=["authentication"]
# )

# Include users router
api_router.include_router(
    users_router,
    prefix="/users",
    tags=["users"]
)

# Include creators router
api_router.include_router(
    creators_router,
    prefix="/creators",
    tags=["creators"],
    dependencies=[Depends(get_current_active_user)]
)

# Include badges router
api_router.include_router(
    badges_router,
    prefix="/badges",
    tags=["badges"],
    dependencies=[Depends(get_current_active_user)]
)

# Include demographics router
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
            "auth": "operational",
            "users": "operational",
            "creators": "operational",
            "badges": "operational", 
            "demographics": "operational",
            # Mark unimplemented endpoints
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