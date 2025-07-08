
##app/core/api/v1/endpoints/auth/router.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.db.session import get_db

router = APIRouter()

@router.get("/")
async def get_root():
    """Root endpoint for this module"""
    return {"message": f"{__name__} endpoint is operational"}

@router.get("/health")
async def health_check():
    """Health check for this module"""
    return {"status": "healthy", "module": __name__}