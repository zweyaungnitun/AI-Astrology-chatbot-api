# app/routers/charts.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Optional
from uuid import UUID
import logging

from app.dependencies.auth import get_current_user
from app.database.session import get_db_session
from app.schemas.chart import ChartCreate, ChartUpdate, ChartResponse, ChartCalculationRequest
from app.services.chart_service import ChartService
from app.services.astrology_service import AstrologyService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/charts", tags=["Charts"])

@router.post("", response_model=ChartResponse)
async def create_chart(
    chart_data: ChartCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new astrology chart."""
    chart_service = ChartService(db)
    internal_user_id = await _get_internal_user_id(db, current_user['uid'])
    chart_data.user_id = internal_user_id
    
    chart = await chart_service.calculate_and_save_chart(chart_data)
    if not chart:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to calculate chart"
        )
    
    return chart

@router.post("/calculate", response_model=dict)
async def calculate_chart(
    calculation_request: ChartCalculationRequest,
    current_user: Optional[dict] = Depends(get_current_user)
):
    """Calculate a chart without saving it (for preview)."""
    try:
        result = AstrologyService.calculate_chart(calculation_request)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("", response_model=List[ChartResponse])
async def get_user_charts(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get all charts for the current user."""
    chart_service = ChartService(db)
    internal_user_id = await _get_internal_user_id(db, current_user['uid'])
    
    charts = await chart_service.get_user_charts(internal_user_id)
    return charts

@router.get("/primary", response_model=Optional[ChartResponse])
async def get_primary_chart(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get the user's primary chart."""
    chart_service = ChartService(db)
    internal_user_id = await _get_internal_user_id(db, current_user['uid'])
    
    chart = await chart_service.get_primary_chart(internal_user_id)
    return chart

@router.get("/{chart_id}", response_model=ChartResponse)
async def get_chart(
    chart_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get a specific chart by ID."""
    chart_service = ChartService(db)
    internal_user_id = await _get_internal_user_id(db, current_user['uid'])
    
    chart = await chart_service.get_chart_by_id(chart_id)
    if not chart or chart.user_id != internal_user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chart not found"
        )
    
    return chart

@router.put("/{chart_id}", response_model=ChartResponse)
async def update_chart(
    chart_id: UUID,
    update_data: ChartUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Update a chart."""
    chart_service = ChartService(db)
    internal_user_id = await _get_internal_user_id(db, current_user['uid'])
    
    # Verify chart belongs to user
    chart = await chart_service.get_chart_by_id(chart_id)
    if not chart or chart.user_id != internal_user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chart not found"
        )
    
    updated_chart = await chart_service.update_chart(chart_id, update_data)
    if not updated_chart:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update chart"
        )
    
    return updated_chart

@router.post("/{chart_id}/recalculate", response_model=ChartResponse)
async def recalculate_chart(
    chart_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Recalculate a chart with current settings."""
    chart_service = ChartService(db)
    internal_user_id = await _get_internal_user_id(db, current_user['uid'])
    
    # Verify chart belongs to user
    chart = await chart_service.get_chart_by_id(chart_id)
    if not chart or chart.user_id != internal_user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chart not found"
        )
    
    recalculated_chart = await chart_service.recalculate_chart(chart_id)
    if not recalculated_chart:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to recalculate chart"
        )
    
    return recalculated_chart

@router.delete("/{chart_id}")
async def delete_chart(
    chart_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Delete a chart."""
    chart_service = ChartService(db)
    internal_user_id = await _get_internal_user_id(db, current_user['uid'])
    
    # Verify chart belongs to user
    chart = await chart_service.get_chart_by_id(chart_id)
    if not chart or chart.user_id != internal_user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chart not found"
        )
    
    success = await chart_service.delete_chart(chart_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to delete chart"
        )
    
    return {"message": "Chart deleted successfully"}

async def _get_internal_user_id(db: AsyncSession, firebase_uid: str) -> UUID:
    """Helper to get internal user ID from Firebase UID."""
    from app.services.user_service import UserService
    user_service = UserService(db)
    user = await user_service.get_user_by_firebase_uid(firebase_uid)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in database"
        )
    return user.id