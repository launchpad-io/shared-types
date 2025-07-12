# app/api/v1/endpoints/creators/router.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional, List
from pydantic import BaseModel, Field, validator
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
import uuid

from app.db.session import get_db
from app.core.auth import get_current_active_user
from app.models.user import User, UserRole
from app.models.gmv_history import GMVHistory
from app.models.analytics import Analytics
from app.utils.logging import get_logger

from app.schemas.creator import CreatorProfileResponse
from app.schemas.user import UserProfileUpdate
from app.schemas.creator import CreatorPerformanceMetrics
from app.schemas.creator import GMVUpdate
from app.schemas.creator import AudienceDemographicsBulkUpdate as AudienceDemographicsUpdate
from app.schemas.badge import BadgeResponse

from app.models.demographics import CreatorAudienceDemographics
from app.schemas.demographics import (
    DemographicsResponse, 
    DemographicsCreate, 
    DemographicsUpdate,
    DemographicsBulkCreate,
    DemographicsSummary
)
from sqlalchemy import text, and_
from sqlalchemy import func




logger = get_logger(__name__)

router = APIRouter()

# --- Enums and Schemas (keep as in your current file) ---
# (No changes to Enums, ProfileResponse, Update, etc. for brevity)

# [ENUMS AND Pydantic SCHEMAS ... as in your file, not shown for brevity]

# ------------------ Endpoints ----------------------

# Get creator profile
@router.get("/profile", response_model=CreatorProfileResponse)
async def get_creator_profile(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != UserRole.CREATOR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This endpoint is only for creators")

    content_categories = getattr(current_user, 'content_categories', [])
    preferred_brands = getattr(current_user, 'preferred_brands', [])

    return CreatorProfileResponse(
        id=str(current_user.id),
        username=current_user.username,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        bio=current_user.bio,
        content_niche=current_user.content_niche,
        content_categories=content_categories,
        follower_count=current_user.follower_count or 0,
        average_views=current_user.average_views or 0,
        engagement_rate=float(current_user.engagement_rate or 0),
        current_gmv=float(current_user.current_gmv or 0),
        total_gmv=float(getattr(current_user, 'total_gmv', 0) or 0),
        tiktok_handle=current_user.tiktok_handle,
        instagram_handle=current_user.instagram_handle,
        discord_handle=current_user.discord_handle,
        youtube_handle=getattr(current_user, 'youtube_handle', None),
        linkedin_handle=getattr(current_user, 'linkedin_handle', None),
        profile_image_url=current_user.profile_image_url,
        created_at=current_user.created_at,
        is_verified=current_user.email_verified,
        badges=[],  # TODO: Implement badge fetching if you persist badges
        preferred_brands=preferred_brands,
        last_active=current_user.last_login

    )

# Update creator profile
@router.patch("/profile", response_model=CreatorProfileResponse)
async def update_creator_profile(
    profile_update: UserProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != UserRole.CREATOR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This endpoint is only for creators")

    update_data = profile_update.dict(exclude_unset=True)

    # if "gender" in update_data:
    #     value = update_data["gender"]
    #     if isinstance(value, Enum):
    #         update_data["gender"] = value.value.lower()  # Always lowercase!
    #     else:
    #         update_data["gender"] = str(value).lower()                                                                                                                      


    # print("Gender being set:", update_data["gender"])


    if 'content_categories' in update_data:
        update_data['content_categories'] = [cat.value for cat in update_data['content_categories']]

    for field, value in update_data.items():
        setattr(current_user, field, value)

    try:
        await db.commit()
        await db.refresh(current_user)
        return await get_creator_profile(current_user, db)
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating profile: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update profile")

# Update creator metrics
@router.patch("/metrics", response_model=dict)
async def update_creator_metrics(
    metrics_update: CreatorPerformanceMetrics,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != UserRole.CREATOR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This endpoint is only for creators")

    update_data = metrics_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)

    try:
        await db.commit()
        await db.refresh(current_user)
        return {
            "message": "Metrics updated successfully",
            "follower_count": current_user.follower_count,
            "average_views": current_user.average_views,
            "engagement_rate": float(current_user.engagement_rate or 0)
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating metrics: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update metrics")

# GMV tracking (create a GMV history record)
@router.post("/gmv", response_model=dict)
async def update_gmv(
    gmv_update: GMVUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != UserRole.CREATOR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This endpoint is only for creators")

    # Update current and total GMV
    if gmv_update.period == "total":
        current_user.total_gmv = Decimal(str(gmv_update.amount))
    else:
        current_user.current_gmv = Decimal(str(gmv_update.amount))
        current_user.total_gmv = (current_user.total_gmv or Decimal('0')) + Decimal(str(gmv_update.amount))

    # Persist GMV history
    new_gmv = GMVHistory(
        id=str(uuid.uuid4()),
        user_id=str(current_user.id),
        period=gmv_update.period,
        amount=gmv_update.amount,
        date=gmv_update.date or datetime.utcnow().date(),
        description=gmv_update.description
    )
    db.add(new_gmv)

    try:
        await db.commit()
        await db.refresh(current_user)
        return {
            "message": "GMV updated successfully",
            "current_gmv": float(current_user.current_gmv or 0),
            "total_gmv": float(getattr(current_user, 'total_gmv', 0) or 0),
            "period": gmv_update.period,
            "amount": gmv_update.amount
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating GMV: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update GMV")

# Get GMV history
@router.get("/gmv/history", response_model=dict)
async def get_gmv_history(
    period: str = Query("30days", pattern="^(7days|30days|90days|all)$"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != UserRole.CREATOR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This endpoint is only for creators")

    result = await db.execute(
        select(GMVHistory).where(GMVHistory.user_id == str(current_user.id))
    )
    history = result.scalars().all()
    history_list = [
        {
            "period": h.period,
            "amount": h.amount,
            "date": h.date,
            "description": h.description,
        }
        for h in history
    ]
    avg_monthly = (
        sum(h["amount"] for h in history_list) / len(history_list) if history_list else 0
    )

    return {
        "period": period,
        "current_gmv": float(current_user.current_gmv or 0),
        "total_gmv": float(getattr(current_user, 'total_gmv', 0) or 0),
        "average_monthly": avg_monthly,
        "growth_rate": 0.0,  # TODO: Calculate if needed
        "history": history_list,
    }
# Add this to app/api/v1/endpoints/creators/router.py


@router.get("/demographics", response_model=List[DemographicsResponse])
async def get_creator_demographics(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all demographics for the current creator"""
    result = await db.execute(
        select(CreatorAudienceDemographics)
        .where(CreatorAudienceDemographics.creator_id == current_user.id)
        .order_by(CreatorAudienceDemographics.age_group)
    )
    demographics = result.scalars().all()
    return demographics

@router.post("/demographics", response_model=DemographicsResponse)
async def create_creator_demographics(
    demographics: DemographicsCreate,  # Now doesn't expect creator_id
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new demographics entry for the current creator"""
    
    # Check if entry already exists
    existing = await db.execute(
        select(CreatorAudienceDemographics)
        .where(
            and_(
                CreatorAudienceDemographics.creator_id == current_user.id,
                CreatorAudienceDemographics.age_group == demographics.age_group,
                CreatorAudienceDemographics.country == demographics.country
            )
        )
    )
    
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Demographics entry already exists for this combination"
        )
    
    # Validate percentage sum
    current_sum = await db.execute(
        select(func.sum(CreatorAudienceDemographics.percentage))
        .where(
            CreatorAudienceDemographics.creator_id == current_user.id
        )
    )
    total = current_sum.scalar() or Decimal('0')
    
    if total + demographics.percentage > Decimal('100'):
        raise HTTPException(
            status_code=400,
            detail=f"Total percentage would exceed 100% (current: {total}%)"
        )
    
    # Create new entry with current user's ID
    new_demographics = CreatorAudienceDemographics(
        creator_id=current_user.id,  # Set from authenticated user
        age_group=demographics.age_group,
        percentage=demographics.percentage,
        country=demographics.country
    )
    db.add(new_demographics)
    await db.commit()
    await db.refresh(new_demographics)
    
    return new_demographics

@router.put("/demographics/{demographics_id}", response_model=DemographicsResponse)
async def update_creator_demographics(
    demographics_id: str,
    demographics_update: DemographicsUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a demographics entry for the current creator"""
    try:
        # Convert string to UUID
        demo_uuid = uuid.UUID(demographics_id)
        
        # Get existing entry and verify ownership
        result = await db.execute(
            select(CreatorAudienceDemographics)
            .where(
                and_(
                    CreatorAudienceDemographics.id == demo_uuid,
                    CreatorAudienceDemographics.creator_id == current_user.id
                )
            )
        )
        demographics = result.scalar_one_or_none()
        
        if not demographics:
            raise HTTPException(
                status_code=404,
                detail="Demographics entry not found or you don't have permission to update it"
            )
        
        # Update fields
        update_data = demographics_update.dict(exclude_unset=True)
        
        # If percentage is being updated, validate the sum
        if 'percentage' in update_data:
            current_sum = await db.execute(
                select(func.sum(CreatorAudienceDemographics.percentage))
                .where(
                    and_(
                        CreatorAudienceDemographics.creator_id == current_user.id,
                        CreatorAudienceDemographics.age_group == demographics.age_group,
                        CreatorAudienceDemographics.gender == demographics.gender,
                        CreatorAudienceDemographics.id != demo_uuid
                    )
                )
            )
            other_sum = current_sum.scalar() or Decimal('0')
            
            if other_sum + Decimal(str(update_data['percentage'])) > Decimal('100'):
                raise HTTPException(
                    status_code=400,
                    detail=f"Total percentage would exceed 100% (current others: {other_sum}%)"
                )
        
        for field, value in update_data.items():
            setattr(demographics, field, value)
        
        await db.commit()
        await db.refresh(demographics)
        
        return demographics
        
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid demographics ID format"
        )

@router.delete("/demographics/{demographics_id}")
async def delete_creator_demographics(
    demographics_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a demographics entry for the current creator"""
    try:
        demo_uuid = uuid.UUID(demographics_id)
        
        result = await db.execute(
            select(CreatorAudienceDemographics)
            .where(
                and_(
                    CreatorAudienceDemographics.id == demo_uuid,
                    CreatorAudienceDemographics.creator_id == current_user.id
                )
            )
        )
        demographics = result.scalar_one_or_none()
        
        if not demographics:
            raise HTTPException(
                status_code=404,
                detail="Demographics entry not found or you don't have permission to delete it"
            )
        
        await db.delete(demographics)
        await db.commit()
        
        return {"detail": "Demographics entry deleted successfully"}
        
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid demographics ID format"
        )

# Add this debug endpoint to your router.py temporarily

@router.get("/demographics/test")
async def test_demographics_setup(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Debug endpoint to test demographics setup"""
    debug_info = {
        "user_id": str(current_user.id),
        "user_email": current_user.email,
        "user_role": current_user.role,
        "checks": {}
    }
    
    # Check 1: Can we import the model?
    try:
        from app.models.demographics import CreatorAudienceDemographics
        debug_info["checks"]["model_import"] = "✓ Success"
    except Exception as e:
        debug_info["checks"]["model_import"] = f"✗ Failed: {str(e)}"
        return debug_info
    
    # Check 2: Can we query the table?
    try:
        result = await db.execute(text("SELECT COUNT(*) FROM users.creator_audience_demographics"))
        count = result.scalar()
        debug_info["checks"]["table_query"] = f"✓ Success - {count} records"
    except Exception as e:
        debug_info["checks"]["table_query"] = f"✗ Failed: {str(e)}"
    
    # Check 3: Can we use SQLAlchemy to query?
    try:
        result = await db.execute(
            select(CreatorAudienceDemographics).limit(1)
        )
        debug_info["checks"]["sqlalchemy_query"] = "✓ Success"
    except Exception as e:
        debug_info["checks"]["sqlalchemy_query"] = f"✗ Failed: {str(e)}"
    
    # Check 4: Check table columns
    try:
        result = await db.execute(
            text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_schema = 'users' 
                AND table_name = 'creator_audience_demographics'
            """)
        )
        columns = result.fetchall()
        debug_info["table_columns"] = [
            {"name": col[0], "type": col[1]} for col in columns
        ]
    except Exception as e:
        debug_info["table_columns"] = f"Error: {str(e)}"
    
    # Check 5: Try to create a test object (without saving)
    try:
        test_demo = CreatorAudienceDemographics(
            creator_id=current_user.id,
            age_group="18-24",
            gender="male",
            percentage=25.5,
            country="US"
        )
        debug_info["checks"]["object_creation"] = "✓ Success"
        debug_info["test_object"] = {
            "creator_id": str(test_demo.creator_id),
            "age_group": test_demo.age_group,
            "gender": test_demo.gender,
            "percentage": float(test_demo.percentage),
            "country": test_demo.country
        }
    except Exception as e:
        debug_info["checks"]["object_creation"] = f"✗ Failed: {str(e)}"
    
    return debug_info

# Badges (remains as calculated; persist if you later add a table)
@router.get("/badges", response_model=List[BadgeResponse])
async def get_creator_badges(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != UserRole.CREATOR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This endpoint is only for creators")

    badges = []
    total_gmv = float(getattr(current_user, 'total_gmv', 0) or 0)
    if total_gmv >= 1000:
        badges.append(BadgeResponse(
            id="gmv_1k",
            name="Rising Star",
            description="Achieved $1,000 in total GMV",
            icon="⭐",
            earned_at=datetime.utcnow(),
            requirements={"gmv": 1000}
        ))
    if total_gmv >= 10000:
        badges.append(BadgeResponse(
            id="gmv_10k",
            name="Top Performer",
            description="Achieved $10,000 in total GMV",
            icon="🌟",
            earned_at=datetime.utcnow(),
            requirements={"gmv": 10000}
        ))
    if total_gmv >= 100000:
        badges.append(BadgeResponse(
            id="gmv_100k",
            name="Elite Creator",
            description="Achieved $100,000 in total GMV",
            icon="💎",
            earned_at=datetime.utcnow(),
            requirements={"gmv": 100000}
        ))
    if current_user.engagement_rate and current_user.engagement_rate >= 5:
        badges.append(BadgeResponse(
            id="high_engagement",
            name="Engagement Master",
            description="Maintained 5%+ engagement rate",
            icon="🔥",
            earned_at=datetime.utcnow(),
            requirements={"engagement_rate": 5}
        ))
    if current_user.follower_count and current_user.follower_count >= 10000:
        badges.append(BadgeResponse(
            id="10k_followers",
            name="Growing Influence",
            description="Reached 10,000 followers",
            icon="👥",
            earned_at=datetime.utcnow(),
            requirements={"followers": 10000}
        ))
    return badges

# Analytics (GET)
@router.get("/analytics", response_model=dict)
async def get_creator_analytics(
    period: str = Query("30days", pattern="^(7days|30days|90days)$"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != UserRole.CREATOR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This endpoint is only for creators")

    result = await db.execute(
        select(Analytics).where(
            Analytics.user_id == str(current_user.id),
            Analytics.period == period
        )
    )
    analytics = result.scalars().first()
    if not analytics:
        raise HTTPException(status_code=404, detail="No analytics found")

    return {
        "period": period,
        "overview": {
            "total_views": analytics.total_views,
            "total_engagement": analytics.total_engagement,
            "follower_growth": analytics.follower_growth,
            "gmv_growth": analytics.gmv_growth,
        },
        "performance": {
            "best_performing_content": analytics.best_performing_content,
            "peak_posting_time": analytics.peak_posting_time,
            "audience_retention": analytics.audience_retention
        },
        "recommendations": analytics.recommendations
    }
