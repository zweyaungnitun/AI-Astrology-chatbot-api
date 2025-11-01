import pytest
from uuid import uuid4
from datetime import date, time

from app.services.chart_service import ChartService
from app.schemas.chart import ChartCreate, ChartUpdate, ChartType, HouseSystem, ZodiacSystem
from app.models.chart import Chart

@pytest.mark.asyncio
class TestChartService:

    async def test_create_chart_success(self, chart_service: ChartService):
        chart_data = ChartCreate(
            user_id=uuid4(),
            chart_type=ChartType.BIRTH_CHART,
            chart_name="Test Chart Success",
            birth_date=date(1990, 1, 1),
            birth_time=time(12, 0, 0),
            birth_location="New York, USA",
            birth_timezone="UTC",
            birth_latitude=40.7128,
            birth_longitude=-74.0060,
            house_system=HouseSystem.PLACIDUS,
            zodiac_system=ZodiacSystem.TROPICAL,
            ayanamsa=0.0,
            is_primary=False,
        )

        chart = await chart_service.calculate_and_save_chart(chart_data)

        assert chart is not None
        assert isinstance(chart, Chart)
        assert chart.id is not None

    async def test_create_chart_primary_replaces_previous(self, chart_service: ChartService):
        user_id = uuid4()

        chart1_data = ChartCreate(
            user_id=user_id,
            chart_type=ChartType.BIRTH_CHART,
            chart_name="Chart 1",
            birth_date=date(1990, 1, 1),
            birth_time=time(12, 0, 0),
            birth_location="New York, USA",
            birth_timezone="UTC",
            birth_latitude=40.7128,
            birth_longitude=-74.0060,
            house_system=HouseSystem.PLACIDUS,
            zodiac_system=ZodiacSystem.TROPICAL,
            ayanamsa=0.0,
            is_primary=True,
        )

        chart2_data = ChartCreate(
            user_id=user_id,
            chart_type=ChartType.BIRTH_CHART,
            chart_name="Chart 2",
            birth_date=date(1991, 2, 2),
            birth_time=time(15, 30, 0),
            birth_location="London, UK",
            birth_timezone="UTC",
            birth_latitude=51.5074,
            birth_longitude=-0.1278,
            house_system=HouseSystem.KOCH,
            zodiac_system=ZodiacSystem.TROPICAL,
            ayanamsa=0.0,
            is_primary=True,
        )

        chart1 = await chart_service.calculate_and_save_chart(chart1_data)
        chart2 = await chart_service.calculate_and_save_chart(chart2_data)

        assert chart1.is_primary is False
        assert chart2.is_primary is True

    async def test_update_chart_primary(self, chart_service: ChartService):
        user_id = uuid4()

        chart1_data = ChartCreate(
            user_id=user_id,
            chart_type=ChartType.BIRTH_CHART,
            chart_name="Chart 1",
            birth_date=date(1990, 1, 1),
            birth_time=time(12, 0, 0),
            birth_location="New York, USA",
            birth_timezone="UTC",
            birth_latitude=40.7128,
            birth_longitude=-74.0060,
            house_system=HouseSystem.PLACIDUS,
            zodiac_system=ZodiacSystem.TROPICAL,
            ayanamsa=0.0,
            is_primary=True,
        )

        chart2_data = ChartCreate(
            user_id=user_id,
            chart_type=ChartType.BIRTH_CHART,
            chart_name="Chart 2",
            birth_date=date(1991, 2, 2),
            birth_time=time(15, 30, 0),
            birth_location="London, UK",
            birth_timezone="UTC",
            birth_latitude=51.5074,
            birth_longitude=-0.1278,
            house_system=HouseSystem.KOCH,
            zodiac_system=ZodiacSystem.TROPICAL,
            ayanamsa=0.0,
            is_primary=False,
        )

        chart1 = await chart_service.calculate_and_save_chart(chart1_data)
        chart2 = await chart_service.calculate_and_save_chart(chart2_data)

        chart2_updated = await chart_service.update_chart(chart2.id, ChartUpdate(is_primary=True))

        assert chart2_updated.is_primary is True
        chart1_refetched = await chart_service.get_chart_by_id(chart1.id)
        assert chart1_refetched.is_primary is False
