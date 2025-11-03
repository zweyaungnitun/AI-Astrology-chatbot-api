import pytest
from uuid import uuid4
from datetime import date, time

from app.services.chart_service import ChartService
from app.services.user_service import UserService
from app.schemas.chart import ChartCreate, ChartUpdate, ChartType, HouseSystem, ZodiacSystem
from app.schemas.user import UserCreate
from app.models.chart import Chart
from app.models.user import User

@pytest.mark.asyncio
class TestChartService:

    async def test_create_chart_success(self, chart_service: ChartService, user_service: UserService):
        # Create a user first
        user = await user_service.create_user(UserCreate(
            firebase_uid="chart_test_user_1",
            email="chart_test1@example.com",
            display_name="Chart Test User 1",
            photo_url="https://example.com/photo.jpg",
            email_verified=True,
        ))
        
        chart_data = ChartCreate(
            user_id=user.id,
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

    async def test_create_chart_primary_replaces_previous(self, chart_service: ChartService, user_service: UserService):
        # Create a user first
        user = await user_service.create_user(UserCreate(
            firebase_uid="chart_test_user_2",
            email="chart_test2@example.com",
            display_name="Chart Test User 2",
            photo_url="https://example.com/photo.jpg",
            email_verified=True,
        ))
        user_id = user.id

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

    async def test_update_chart_primary(self, chart_service: ChartService, user_service: UserService):
        # Create a user first
        user = await user_service.create_user(UserCreate(
            firebase_uid="chart_test_user_3",
            email="chart_test3@example.com",
            display_name="Chart Test User 3",
            photo_url="https://example.com/photo.jpg",
            email_verified=True,
        ))
        user_id = user.id

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

    async def test_get_user_charts(self, chart_service: ChartService, user_service: UserService):
        """Test getting all charts for a user."""
        # Create a user first
        user = await user_service.create_user(UserCreate(
            firebase_uid="chart_test_user_get_charts",
            email="chart_test_get_charts@example.com",
            display_name="Chart Test User Get Charts",
            photo_url="https://example.com/photo.jpg",
            email_verified=True,
        ))
        user_id = user.id

        # Initially, user should have no charts
        charts = await chart_service.get_user_charts(user_id)
        assert len(charts) == 0

        # Create first chart
        chart1_data = ChartCreate(
            user_id=user_id,
            chart_type=ChartType.BIRTH_CHART,
            chart_name="First Chart",
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
        chart1 = await chart_service.calculate_and_save_chart(chart1_data)

        # Now user should have 1 chart
        charts = await chart_service.get_user_charts(user_id)
        assert len(charts) == 1
        assert charts[0].id == chart1.id
        assert charts[0].chart_name == "First Chart"

        # Create second chart
        chart2_data = ChartCreate(
            user_id=user_id,
            chart_type=ChartType.BIRTH_CHART,
            chart_name="Second Chart",
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
        chart2 = await chart_service.calculate_and_save_chart(chart2_data)

        # Now user should have 2 charts, ordered by created_at desc
        charts = await chart_service.get_user_charts(user_id)
        assert len(charts) == 2
        # Newest chart should be first
        assert charts[0].id == chart2.id
        assert charts[0].chart_name == "Second Chart"
        assert charts[1].id == chart1.id
        assert charts[1].chart_name == "First Chart"

    async def test_get_user_charts_isolation(self, chart_service: ChartService, user_service: UserService):
        """Test that user charts are isolated - user2 doesn't see user1's charts."""
        # Create two users
        user1 = await user_service.create_user(UserCreate(
            firebase_uid="chart_test_user1_isolation",
            email="chart_test1_isolation@example.com",
            display_name="Chart Test User 1 Isolation",
            photo_url="https://example.com/photo.jpg",
            email_verified=True,
        ))
        assert user1 is not None, "Failed to create user1"
        
        user2 = await user_service.create_user(UserCreate(
            firebase_uid="chart_test_user2_isolation",
            email="chart_test2_isolation@example.com",
            display_name="Chart Test User 2 Isolation",
            photo_url="https://example.com/photo.jpg",
            email_verified=True,
        ))
        assert user2 is not None, "Failed to create user2"

        # Create chart for user1
        chart1_data = ChartCreate(
            user_id=user1.id,
            chart_type=ChartType.BIRTH_CHART,
            chart_name="User1 Chart",
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
        await chart_service.calculate_and_save_chart(chart1_data)

        # User1 should have 1 chart
        user1_charts = await chart_service.get_user_charts(user1.id)
        assert len(user1_charts) == 1
        assert user1_charts[0].chart_name == "User1 Chart"

        # User2 should have 0 charts
        user2_charts = await chart_service.get_user_charts(user2.id)
        assert len(user2_charts) == 0
