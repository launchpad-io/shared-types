# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.endpoints.creators import router as creators_router
from app.api.v1.endpoints.badges.router import router as badges_router  # Fixed import path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Creator Service",
    version="1.0.0",
    description="Creator profile management service with badges"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "creator-service"}

# Include routers
app.include_router(creators_router, prefix="/api/v1/creators", tags=["creators"])
app.include_router(badges_router, prefix="/api/v1/badges", tags=["badges"])

# Debug: List all routes
@app.get("/routes")
async def list_routes():
    """List all available routes (for debugging)"""
    routes = []
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            routes.append({
                "path": route.path,
                "methods": list(route.methods) if route.methods else [],
                "name": route.name
            })
    return {"routes": routes}

@app.on_event("startup")
async def startup_event():
    logger.info("Creator Service started on port 8006")
    logger.info(f"Available routes: {[route.path for route in app.routes if hasattr(route, 'path')]}")