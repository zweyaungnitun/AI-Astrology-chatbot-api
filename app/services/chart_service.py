from uuid import UUID
from typing import Optional, List
from datetime import datetime
import logging

from sqlmodel import select, delete
from sqlmodel.ext.asyncio.session import AsyncSession

from app.schemas.chart import ChartCreate, ChartUpdate, ChartCalculationRequest
from app.models.chart import Chart
from app.services.astrology_service import AstrologyService

logger = logging.getLogger(__name__)


class ChartService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.astrology_service = AstrologyService()

    async def calculate_and_save_chart(self, chart_data: ChartCreate) -> Optional[Chart]:
        try:
            calc_req = ChartCalculationRequest(
                birth_date=chart_data.birth_date,
                birth_time=chart_data.birth_time,
                birth_location=chart_data.birth_location,
                birth_timezone=chart_data.birth_timezone,
                birth_latitude=chart_data.birth_latitude,
                birth_longitude=chart_data.birth_longitude,
                house_system=chart_data.house_system,
                zodiac_system=chart_data.zodiac_system,
                ayanamsa=chart_data.ayanamsa
            )
            result = await self.astrology_service.calculate_chart(calc_req)

            chart = Chart(
                **chart_data.model_dump(),
                planetary_positions=result["planetary_positions"],
                house_positions=result["house_positions"],
                aspects=result["aspects"],
                summary=result["summary"],
                calculation_time=result["calculation_time"]
            )

            if chart.is_primary:
                await self._remove_other_primary_charts(chart.user_id)

            self.db.add(chart)
            await self.db.commit()
            await self.db.refresh(chart)
            return chart

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating chart: {e}")
            return None

    async def _remove_other_primary_charts(self, user_id: UUID):
        result = await self.db.exec(select(Chart).where((Chart.user_id == user_id) & (Chart.is_primary == True)))
        for chart in result.all():
            chart.is_primary = False
        await self.db.commit()

    async def get_chart_by_id(self, chart_id: UUID) -> Optional[Chart]:
        result = await self.db.exec(select(Chart).where(Chart.id == chart_id))
        return result.first()

    async def get_user_charts(self, user_id: UUID) -> List[Chart]:
        result = await self.db.exec(select(Chart).where(Chart.user_id == user_id).order_by(Chart.created_at.desc()))
        return result.all()

    async def get_primary_chart(self, user_id: UUID) -> Optional[Chart]:
        result = await self.db.exec(select(Chart).where((Chart.user_id == user_id) & (Chart.is_primary == True)))
        return result.first()

    async def update_chart(self, chart_id: UUID, update_data: ChartUpdate) -> Optional[Chart]:
        chart = await self.get_chart_by_id(chart_id)
        if not chart:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        if update_dict.get("is_primary"):
            await self._remove_other_primary_charts(chart.user_id)
        for k, v in update_dict.items():
            setattr(chart, k, v)

        chart.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(chart)
        return chart

    async def delete_chart(self, chart_id: UUID) -> bool:
        chart = await self.get_chart_by_id(chart_id)
        if not chart:
            return False
        await self.db.exec(delete(Chart).where(Chart.id == chart_id))
        await self.db.commit()
        return True

    async def recalculate_chart(self, chart_id: UUID) -> Optional[Chart]:
        chart = await self.get_chart_by_id(chart_id)
        if not chart:
            return None

        calc_req = ChartCalculationRequest(
            birth_date=chart.birth_date,
            birth_time=chart.birth_time,
            birth_location=chart.birth_location,
            birth_timezone=chart.birth_timezone,
            birth_latitude=chart.birth_latitude,
            birth_longitude=chart.birth_longitude,
            house_system=chart.house_system,
            zodiac_system=chart.zodiac_system,
            ayanamsa=chart.ayanamsa
        )
        result = await self.astrology_service.calculate_chart(calc_req)

        chart.planetary_positions = result["planetary_positions"]
        chart.house_positions = result["house_positions"]
        chart.aspects = result["aspects"]
        chart.summary = result["summary"]
        chart.calculation_time = result["calculation_time"]
        chart.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(chart)
        return chart
