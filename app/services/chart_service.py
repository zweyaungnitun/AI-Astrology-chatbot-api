from sqlmodel import select, update, delete
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Optional, List, Dict, Any
from uuid import UUID
import logging
from datetime import datetime

from app.schemas.chart import Chart, ChartCreate, ChartUpdate
from app.services.astrology_service import AstrologyService, ChartCalculationRequest

logger = logging.getLogger(__name__)

class ChartService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def calculate_and_save_chart(self, chart_data: ChartCreate) -> Optional[Chart]:
        """Calculate and save a new chart."""
        try:
            # Prepare calculation request
            calculation_request = ChartCalculationRequest(
                birth_date=chart_data.birth_date,
                birth_time=chart_data.birth_time,
                birth_location=chart_data.birth_location,
                birth_timezone=chart_data.birth_timezone,
                house_system=chart_data.house_system,
                zodiac_system=chart_data.zodiac_system,
                ayanamsa=chart_data.ayanamsa
            )
            
            # Calculate chart
            calculation_result = AstrologyService.calculate_chart(calculation_request)
            
            # Create chart object
            chart = Chart(
                **chart_data.dict(),
                planetary_positions=calculation_result["planetary_positions"],
                house_positions=calculation_result["house_positions"],
                aspects=calculation_result["aspects"],
                summary=calculation_result["summary"],
                calculation_time=calculation_result["calculation_time"]
            )
            
            # If this is primary, ensure no other primary charts exist for this user
            if chart.is_primary:
                await self._remove_other_primary_charts(chart.user_id)
            
            self.db.add(chart)
            await self.db.commit()
            await self.db.refresh(chart)
            
            logger.info(f"Created chart {chart.id} for user {chart.user_id}")
            return chart
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating chart: {str(e)}")
            return None

    async def _remove_other_primary_charts(self, user_id: UUID) -> None:
        """Remove primary status from other charts for this user."""
        try:
            # Find existing primary charts
            existing_primary = await self.db.exec(
                select(Chart).where(
                    (Chart.user_id == user_id) & 
                    (Chart.is_primary == True)
                )
            )
            existing_primary = existing_primary.all()
            
            # Remove primary status
            for chart in existing_primary:
                chart.is_primary = False
            
            await self.db.commit()
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error removing primary charts: {str(e)}")

    async def get_chart_by_id(self, chart_id: UUID) -> Optional[Chart]:
        """Get chart by ID."""
        try:
            result = await self.db.exec(select(Chart).where(Chart.id == chart_id))
            return result.first()
        except Exception as e:
            logger.error(f"Error getting chart {chart_id}: {str(e)}")
            return None

    async def get_user_charts(self, user_id: UUID) -> List[Chart]:
        """Get all charts for a user."""
        try:
            result = await self.db.exec(
                select(Chart).where(Chart.user_id == user_id).order_by(Chart.created_at.desc())
            )
            return result.all()
        except Exception as e:
            logger.error(f"Error getting charts for user {user_id}: {str(e)}")
            return []

    async def get_primary_chart(self, user_id: UUID) -> Optional[Chart]:
        """Get user's primary chart."""
        try:
            result = await self.db.exec(
                select(Chart).where(
                    (Chart.user_id == user_id) & 
                    (Chart.is_primary == True)
                )
            )
            return result.first()
        except Exception as e:
            logger.error(f"Error getting primary chart for user {user_id}: {str(e)}")
            return None

    async def update_chart(self, chart_id: UUID, update_data: ChartUpdate) -> Optional[Chart]:
        """Update chart information."""
        try:
            chart = await self.get_chart_by_id(chart_id)
            if not chart:
                return None

            update_dict = update_data.dict(exclude_unset=True)
            
            # Handle primary chart logic
            if "is_primary" in update_dict and update_dict["is_primary"]:
                await self._remove_other_primary_charts(chart.user_id)
            
            for field, value in update_dict.items():
                setattr(chart, field, value)
            
            chart.updated_at = datetime.utcnow()
            
            await self.db.commit()
            await self.db.refresh(chart)
            
            return chart
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating chart {chart_id}: {str(e)}")
            return None

    async def delete_chart(self, chart_id: UUID) -> bool:
        """Delete a chart."""
        try:
            chart = await self.get_chart_by_id(chart_id)
            if not chart:
                return False

            await self.db.exec(delete(Chart).where(Chart.id == chart_id))
            await self.db.commit()
            
            logger.info(f"Deleted chart {chart_id}")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting chart {chart_id}: {str(e)}")
            return False

    async def recalculate_chart(self, chart_id: UUID) -> Optional[Chart]:
        """Recalculate a chart with current settings."""
        try:
            chart = await self.get_chart_by_id(chart_id)
            if not chart:
                return None

            # Prepare calculation request
            calculation_request = ChartCalculationRequest(
                birth_date=chart.birth_date,
                birth_time=chart.birth_time,
                birth_location=chart.birth_location,
                birth_timezone=chart.birth_timezone,
                house_system=chart.house_system,
                zodiac_system=chart.zodiac_system,
                ayanamsa=chart.ayanamsa
            )
            
            # Recalculate chart
            calculation_result = AstrologyService.calculate_chart(calculation_request)
            
            # Update chart data
            chart.planetary_positions = calculation_result["planetary_positions"]
            chart.house_positions = calculation_result["house_positions"]
            chart.aspects = calculation_result["aspects"]
            chart.summary = calculation_result["summary"]
            chart.calculation_time = calculation_result["calculation_time"]
            chart.updated_at = datetime.utcnow()
            
            await self.db.commit()
            await self.db.refresh(chart)
            
            logger.info(f"Recalculated chart {chart_id}")
            return chart
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error recalculating chart {chart_id}: {str(e)}")
            return None