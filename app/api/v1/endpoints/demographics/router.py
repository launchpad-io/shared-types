# app/api/v1/endpoints/demographics/router.py
"""
Demographics API endpoints
Handles creator audience demographics data
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import List, Optional, Dict
from decimal import Decimal
import uuid
from datetime import datetime

from app.db.session import get_db
from app.models.demographics import CreatorAudienceDemographics, GenderType
from app.schemas.demographics import (
    DemographicsResponse,
    DemographicsCreate,
    DemographicsUpdate,
    DemographicsSummary,
    DemographicsBulkCreate
)
from app.core.dependencies import get_current_active_user
from app.models.user import User

router = APIRouter()

@router.get("/creator/{creator_id}", response_model=List[DemographicsResponse])
async def get_creator_demographics(
    creator_id: uuid.UUID = Path(..., description="Creator's UUID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all demographics data for a specific creator.
    
    - **creator_id**: UUID of the creator
    - Returns list of demographic entries with age groups, gender, and percentages
    """
    try:
        result = await db.execute(
            select(CreatorAudienceDemographics)
            .where(CreatorAudienceDemographics.creator_id == creator_id)
            .order_by(
                CreatorAudienceDemographics.age_group,
                CreatorAudienceDemographics.gender,
                CreatorAudienceDemographics.country
            )
        )
        demographics = result.scalars().all()
        
        if not demographics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No demographics found for creator {creator_id}"
            )
        
        return demographics
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch demographics: {str(e)}"
        )

@router.get("/creator/{creator_id}/summary", response_model=DemographicsSummary)
async def get_creator_demographics_summary(
    creator_id: uuid.UUID = Path(..., description="Creator's UUID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get summarized demographics data for a creator.
    
    Returns aggregated data by age group, gender, and country.
    """
    try:
        # Get all demographics
        result = await db.execute(
            select(CreatorAudienceDemographics)
            .where(CreatorAudienceDemographics.creator_id == creator_id)
        )
        demographics = result.scalars().all()
        
        if not demographics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No demographics found for creator {creator_id}"
            )
        
        # Aggregate data
        age_distribution = {}
        gender_distribution = {}
        country_distribution = {}
        total_percentage = Decimal('0')
        
        for demo in demographics:
            # Age distribution
            age_distribution[demo.age_group] = age_distribution.get(demo.age_group, Decimal('0')) + demo.percentage
            
            # Gender distribution
            gender_distribution[demo.gender.value] = gender_distribution.get(demo.gender.value, Decimal('0')) + demo.percentage
            
            # Country distribution
            if demo.country:
                country_distribution[demo.country] = country_distribution.get(demo.country, Decimal('0')) + demo.percentage
            
            total_percentage += demo.percentage
        
        return DemographicsSummary(
            creator_id=creator_id,
            total_entries=len(demographics),
            total_percentage=total_percentage,
            age_distribution=age_distribution,
            gender_distribution=gender_distribution,
            country_distribution=country_distribution,
            last_updated=max(d.updated_at for d in demographics) if demographics else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch demographics summary: {str(e)}"
        )

@router.post("/", response_model=DemographicsResponse, status_code=status.HTTP_201_CREATED)
async def create_demographics(
    demographics: DemographicsCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new demographics entry for a creator.
    
    Validates that the total percentage for an age/gender combination doesn't exceed 100%.
    """
    try:
        # Check if entry already exists
        existing = await db.execute(
            select(CreatorAudienceDemographics)
            .where(
                and_(
                    CreatorAudienceDemographics.creator_id == demographics.creator_id,
                    CreatorAudienceDemographics.age_group == demographics.age_group,
                    CreatorAudienceDemographics.gender == demographics.gender,
                    CreatorAudienceDemographics.country == demographics.country
                )
            )
        )
        
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Demographics entry already exists for this combination"
            )
        
        # Validate percentage sum
        current_sum = await db.execute(
            select(func.sum(CreatorAudienceDemographics.percentage))
            .where(
                and_(
                    CreatorAudienceDemographics.creator_id == demographics.creator_id,
                    CreatorAudienceDemographics.age_group == demographics.age_group,
                    CreatorAudienceDemographics.gender == demographics.gender
                )
            )
        )
        total = current_sum.scalar() or Decimal('0')
        
        if total + demographics.percentage > Decimal('100'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Total percentage for {demographics.age_group}/{demographics.gender} would exceed 100% (current: {total}%)"
            )
        
        # Create new entry
        new_demographics = CreatorAudienceDemographics(**demographics.dict())
        db.add(new_demographics)
        await db.commit()
        await db.refresh(new_demographics)
        
        return new_demographics
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create demographics: {str(e)}"
        )

@router.post("/bulk", response_model=List[DemographicsResponse], status_code=status.HTTP_201_CREATED)
async def bulk_create_demographics(
    demographics_list: DemographicsBulkCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Bulk create or update demographics for a creator.
    
    This will replace all existing demographics for the creator.
    """
    try:
        creator_id = demographics_list.creator_id
        
        # Validate total percentages
        validation_totals = {}
        for demo in demographics_list.demographics:
            key = f"{demo.age_group}/{demo.gender}"
            validation_totals[key] = validation_totals.get(key, Decimal('0')) + demo.percentage
        
        for key, total in validation_totals.items():
            if total > Decimal('100'):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Total percentage for {key} exceeds 100% (total: {total}%)"
                )
        
        # Delete existing demographics
        await db.execute(
            select(CreatorAudienceDemographics)
            .where(CreatorAudienceDemographics.creator_id == creator_id)
            .execution_options(synchronize_session="fetch")
        )
        
        # Create new demographics
        new_demographics = []
        for demo_data in demographics_list.demographics:
            new_demo = CreatorAudienceDemographics(
                creator_id=creator_id,
                **demo_data.dict()
            )
            db.add(new_demo)
            new_demographics.append(new_demo)
        
        await db.commit()
        
        # Refresh all objects
        for demo in new_demographics:
            await db.refresh(demo)
        
        return new_demographics
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk create demographics: {str(e)}"
        )

@router.put("/{demographics_id}", response_model=DemographicsResponse)
async def update_demographics(
    demographics_id: uuid.UUID = Path(..., description="Demographics entry ID"),
    demographics_update: DemographicsUpdate = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update an existing demographics entry.
    """
    try:
        # Get existing entry
        result = await db.execute(
            select(CreatorAudienceDemographics)
            .where(CreatorAudienceDemographics.id == demographics_id)
        )
        demographics = result.scalar_one_or_none()
        
        if not demographics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Demographics entry not found"
            )
        
        # Update fields
        update_data = demographics_update.dict(exclude_unset=True)
        
        # If percentage is being updated, validate the sum
        if 'percentage' in update_data:
            current_sum = await db.execute(
                select(func.sum(CreatorAudienceDemographics.percentage))
                .where(
                    and_(
                        CreatorAudienceDemographics.creator_id == demographics.creator_id,
                        CreatorAudienceDemographics.age_group == demographics.age_group,
                        CreatorAudienceDemographics.gender == demographics.gender,
                        CreatorAudienceDemographics.id != demographics_id
                    )
                )
            )
            other_sum = current_sum.scalar() or Decimal('0')
            
            if other_sum + update_data['percentage'] > Decimal('100'):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Total percentage would exceed 100% (current others: {other_sum}%)"
                )
        
        for field, value in update_data.items():
            setattr(demographics, field, value)
        
        await db.commit()
        await db.refresh(demographics)
        
        return demographics
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update demographics: {str(e)}"
        )

@router.delete("/{demographics_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_demographics(
    demographics_id: uuid.UUID = Path(..., description="Demographics entry ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a demographics entry.
    """
    try:
        result = await db.execute(
            select(CreatorAudienceDemographics)
            .where(CreatorAudienceDemographics.id == demographics_id)
        )
        demographics = result.scalar_one_or_none()
        
        if not demographics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Demographics entry not found"
            )
        
        await db.delete(demographics)
        await db.commit()
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete demographics: {str(e)}"
        )

@router.get("/search", response_model=List[DemographicsResponse])
async def search_demographics(
    age_group: Optional[str] = Query(None, regex="^(13-17|18-24|25-34|35-44|45-54|55\+)$"),
    gender: Optional[GenderType] = None,
    country: Optional[str] = None,
    min_percentage: Optional[float] = Query(None, ge=0, le=100),
    max_percentage: Optional[float] = Query(None, ge=0, le=100),
    creator_ids: Optional[List[uuid.UUID]] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Search demographics across creators with filtering options.
    
    - **age_group**: Filter by age group (13-17, 18-24, 25-34, 35-44, 45-54, 55+)
    - **gender**: Filter by gender
    - **country**: Filter by country
    - **min_percentage**: Minimum percentage threshold
    - **max_percentage**: Maximum percentage threshold
    - **creator_ids**: List of creator IDs to filter by
    - **limit**: Number of results to return (max 1000)
    - **offset**: Number of results to skip
    """
    try:
        query = select(CreatorAudienceDemographics)
        
        # Apply filters
        conditions = []
        if age_group:
            conditions.append(CreatorAudienceDemographics.age_group == age_group)
        if gender:
            conditions.append(CreatorAudienceDemographics.gender == gender)
        if country:
            conditions.append(CreatorAudienceDemographics.country == country)
        if min_percentage is not None:
            conditions.append(CreatorAudienceDemographics.percentage >= min_percentage)
        if max_percentage is not None:
            conditions.append(CreatorAudienceDemographics.percentage <= max_percentage)
        if creator_ids:
            conditions.append(CreatorAudienceDemographics.creator_id.in_(creator_ids))
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Apply ordering and pagination
        query = query.order_by(
            CreatorAudienceDemographics.creator_id,
            CreatorAudienceDemographics.percentage.desc()
        )
        query = query.offset(offset).limit(limit)
        
        result = await db.execute(query)
        demographics = result.scalars().all()
        
        return demographics
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search demographics: {str(e)}"
        )