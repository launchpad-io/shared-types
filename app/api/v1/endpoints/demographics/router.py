"""
Demographics API Router
Dedicated endpoints for demographic management and visualization
"""
##app/core/api/v1/endpoints/demogprahics/router.py
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from fastapi import (
    APIRouter, Depends, HTTPException, status, 
    UploadFile, File, Query, Response
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.dependencies import get_current_active_user, require_creator_role
from app.models.user import User, UserRole
from app.schemas.demographics import (
    DemographicsVisualizationResponse,
    DemographicsImportResponse,
    DemographicsAnalyticsResponse,
    DemographicsSearchFilters,
    DemographicsComparisonRequest,
    DemographicsComparisonResponse,
    DemographicsSummaryResponse,
    DemographicsTemplateFormat
)
from app.schemas.creator import (
    AudienceDemographicCreate,
    AudienceDemographicResponse,
    AudienceDemographicsBulkUpdate
)
from app.services.demographics import (
    DemographicsService,
    DemographicsImportService,
    DemographicsVisualizationService,
    DemographicsValidator
)
from app.core.cache import cache
from app.utils.logging import get_logger
from app.core.exceptions import (
    NotFoundException,
    ValidationException,
    BusinessLogicException
)

logger = get_logger(__name__)

router = APIRouter(
    prefix="/demographics",
    tags=["demographics"],
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Forbidden"},
        404: {"description": "Not found"},
        422: {"description": "Validation error"}
    }
)


# Template download endpoints
@router.get("/template/{format}", 
           summary="Download demographics import template",
           response_class=Response)
async def download_template(
    format: DemographicsTemplateFormat,
    current_user: User = Depends(get_current_active_user)
) -> Response:
    """
    Download a template file for demographics import
    
    Args:
        format: Template format (csv or xlsx)
        
    Returns:
        Template file for download
    """
    try:
        import_service = DemographicsImportService()
        
        # Generate template
        content = import_service.generate_template(format.value)
        
        # Set appropriate headers
        if format == DemographicsTemplateFormat.csv:
            media_type = "text/csv"
            filename = "demographics_template.csv"
        else:
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = "demographics_template.xlsx"
        
        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except Exception as e:
        logger.error(f"Error generating template: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate template"
        )


# Import endpoints
@router.post("/import", 
            response_model=DemographicsImportResponse,
            summary="Import demographics from file")
async def import_demographics(
    file: UploadFile = File(..., description="CSV or Excel file"),
    creator_id: Optional[UUID] = Query(None, description="Creator ID (admin only)"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> DemographicsImportResponse:
    """
    Import demographics from CSV or Excel file
    
    File format requirements:
    - Headers: age_group, gender, percentage, country (optional)
    - Age groups: 13-17, 18-24, 25-34, 35-44, 45-54, 55+
    - Genders: male, female, non_binary, prefer_not_to_say
    - Percentages must sum to ~100% per gender
    """
    try:
        # Determine target creator
        if creator_id and current_user.role == UserRole.admin:
            target_creator_id = creator_id
        elif current_user.role == UserRole.creator:
            target_creator_id = current_user.id
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only creators can import their own demographics"
            )
        
        # Validate file type
        if not file.filename.lower().endswith(('.csv', '.xlsx', '.xls')):
            raise ValidationException("File must be CSV or Excel format")
        
        # Read file content
        content = await file.read()
        
        # Import demographics
        import_service = DemographicsImportService()
        valid_demographics, errors = await import_service.import_from_file(
            content,
            file.filename,
            file.content_type
        )
        
        # If no valid data, return error
        if not valid_demographics and errors:
            return DemographicsImportResponse(
                success=False,
                imported_count=0,
                error_count=len(errors),
                errors=errors[:10],  # Limit errors in response
                message="No valid demographics found in file"
            )
        
        # Save valid demographics
        if valid_demographics:
            demographics_service = DemographicsService(db)
            bulk_update = AudienceDemographicsBulkUpdate(demographics=valid_demographics)
            
            await demographics_service.update_demographics_bulk(
                target_creator_id,
                bulk_update
            )
        
        return DemographicsImportResponse(
            success=True,
            imported_count=len(valid_demographics),
            error_count=len(errors),
            errors=errors[:10] if errors else [],
            message=f"Successfully imported {len(valid_demographics)} demographics"
        )
        
    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error importing demographics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to import demographics"
        )


# Visualization endpoints
@router.get("/visualization/{creator_id}",
           response_model=DemographicsVisualizationResponse,
           summary="Get demographics visualization data")
@cache(expire=300)  # Cache for 5 minutes
async def get_demographics_visualization(
    creator_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> DemographicsVisualizationResponse:
    """
    Get demographic data formatted for charts and visualizations
    
    Returns data for:
    - Gender distribution (pie/donut chart)
    - Age distribution (bar chart)
    - Location distribution (map/list)
    - Detailed breakdown
    """
    try:
        viz_service = DemographicsVisualizationService(db)
        data = await viz_service.get_combined_demographics_data(creator_id)
        
        return DemographicsVisualizationResponse(**data)
        
    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Creator not found"
        )
    except Exception as e:
        logger.error(f"Error getting visualization data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get visualization data"
        )


# Analytics endpoints
@router.post("/analytics",
            response_model=DemographicsAnalyticsResponse,
            summary="Get aggregated demographics analytics")
async def get_demographics_analytics(
    filters: DemographicsSearchFilters,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> DemographicsAnalyticsResponse:
    """
    Get aggregated analytics across multiple creators
    
    Useful for agencies to understand their creator network demographics
    """
    try:
        # Only agencies and admins can access network analytics
        if current_user.role not in [UserRole.agency, UserRole.admin]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only agencies can access network analytics"
            )
        
        demographics_service = DemographicsService(db)
        
        # Build filter dict
        filter_dict = {}
        if filters.age_groups:
            filter_dict['age_groups'] = filters.age_groups
        if filters.genders:
            filter_dict['genders'] = filters.genders
        if filters.countries:
            filter_dict['countries'] = filters.countries
        if filters.min_percentage is not None:
            filter_dict['min_percentage'] = filters.min_percentage
        
        # Search creators
        results = await demographics_service.search_creators_by_demographics(
            filter_dict,
            limit=100  # Get more for analytics
        )
        
        # Aggregate demographics
        total_creators = results['total']
        
        # Calculate aggregate stats
        gender_totals = {"male": 0, "female": 0, "non_binary": 0, "prefer_not_to_say": 0}
        age_totals = {}
        country_totals = {}
        
        # This is simplified - in production, you'd aggregate from actual demographics
        for creator in results['creators']:
            # Would need to fetch and aggregate each creator's demographics
            pass
        
        return DemographicsAnalyticsResponse(
            total_creators=total_creators,
            gender_distribution=gender_totals,
            age_distribution=age_totals,
            top_countries=[],
            average_metrics={
                "avg_female_percentage": 0,
                "avg_youth_percentage": 0,
                "avg_countries_per_creator": 0
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get analytics"
        )


# Comparison endpoints
@router.post("/compare",
            response_model=DemographicsComparisonResponse,
            summary="Compare demographics across creators")
async def compare_demographics(
    request: DemographicsComparisonRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> DemographicsComparisonResponse:
    """
    Compare demographics across multiple creators
    
    Useful for agencies to compare creator audiences
    """
    try:
        if len(request.creator_ids) < 2:
            raise ValidationException("At least 2 creators required for comparison")
        
        if len(request.creator_ids) > 5:
            raise ValidationException("Maximum 5 creators for comparison")
        
        viz_service = DemographicsVisualizationService(db)
        comparison_data = await viz_service.get_demographic_comparison_data(
            request.creator_ids
        )
        
        return DemographicsComparisonResponse(**comparison_data)
        
    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error comparing demographics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compare demographics"
        )


# Search endpoints
@router.post("/search",
            response_model=List[UUID],
            summary="Search creators by demographics")
async def search_by_demographics(
    filters: DemographicsSearchFilters,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> List[UUID]:
    """
    Search creators by demographic criteria
    
    Returns list of creator IDs matching the filters
    """
    try:
        demographics_service = DemographicsService(db)
        
        # Build filter dict
        filter_dict = {}
        if filters.age_groups:
            filter_dict['age_groups'] = filters.age_groups
        if filters.genders:
            filter_dict['genders'] = filters.genders
        if filters.countries:
            filter_dict['countries'] = filters.countries
        if filters.min_percentage is not None:
            filter_dict['min_percentage'] = filters.min_percentage
        
        results = await demographics_service.search_creators_by_demographics(
            filter_dict,
            limit=limit,
            offset=offset
        )
        
        # Return just creator IDs
        return [creator.id for creator in results['creators']]
        
    except Exception as e:
        logger.error(f"Error searching demographics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search demographics"
        )


# Summary endpoint
@router.get("/summary/{creator_id}",
           response_model=DemographicsSummaryResponse,
           summary="Get demographics summary")
async def get_demographics_summary(
    creator_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> DemographicsSummaryResponse:
    """
    Get a quick summary of creator demographics
    
    Useful for profile cards and quick views
    """
    try:
        demographics_service = DemographicsService(db)
        summary = await demographics_service.get_demographics_summary(creator_id)
        
        return DemographicsSummaryResponse(**summary)
        
    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Creator not found"
        )
    except Exception as e:
        logger.error(f"Error getting summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get demographics summary"
        )


# Validation endpoint
@router.post("/validate",
            summary="Validate demographics data")
async def validate_demographics(
    demographics: AudienceDemographicsBulkUpdate,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Validate demographics data without saving
    
    Useful for pre-validation before import
    """
    try:
        validator = DemographicsValidator()
        result = validator.validate_bulk_demographics(demographics.demographics)
        
        return {
            "is_valid": result.is_valid,
            "errors": result.errors,
            "warnings": result.warnings
        }
        
    except Exception as e:
        logger.error(f"Error validating demographics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate demographics"
        )