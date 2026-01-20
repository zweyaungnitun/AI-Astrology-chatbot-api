from typing import Optional, Dict, Any, List
from datetime import datetime, date, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# Enums imported from SQLModel layer (OK to reuse enums)
from app.models.chart import ChartType, HouseSystem, ZodiacSystem

class ChartBase(BaseModel):
    chart_type: ChartType = ChartType.BIRTH_CHART
    chart_name: Optional[str] = "Birth Chart"

    birth_date: date
    birth_time: time
    birth_location: str
    birth_timezone: str = "UTC"

    birth_latitude: Optional[float] = None
    birth_longitude: Optional[float] = None

    house_system: HouseSystem = HouseSystem.PLACIDUS
    zodiac_system: ZodiacSystem = ZodiacSystem.TROPICAL
    ayanamsa: Optional[float] = 0.0

    is_primary: bool = False

class PlanetPosition(BaseModel):
    planet: str
    sign: str
    degree: float
    longitude: float
    house: int
    retrograde: bool


class HousePosition(BaseModel):
    house: int
    sign: str
    degree: float
    longitude: float

class ChartCreate(ChartBase):
    """Schema for creating a new chart. Inherits all fields from ChartBase."""
    pass

class ChartUpdate(ChartBase):
    """Schema for updating a chart's name or primary status."""
    chart_name: Optional[str] = None
    is_primary: Optional[bool] = None

# --- Output Schemas ---

class ChartResponse(BaseModel):
    id: UUID

    chart_type: ChartType
    chart_name: Optional[str]

    birth_date: date
    birth_time: time
    birth_location: str
    birth_timezone: str

    house_system: HouseSystem
    zodiac_system: ZodiacSystem

    planetary_positions: List[PlanetPosition]
    house_positions: List[HousePosition]

    aspects: List[Dict[str, Any]]
    summary: Dict[str, Any]

    is_primary: bool

    created_at: datetime
    updated_at: datetime
    calculation_time: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


# --- Service/Utility Schemas ---

class ChartCalculationRequest(BaseModel):
    """Schema for a request to calculate chart data without creating a chart entry."""
    birth_date: date
    birth_time: time
    birth_location: str
    birth_timezone: str = "UTC"
    birth_latitude: Optional[float] = None
    birth_longitude: Optional[float] = None
    house_system: HouseSystem = HouseSystem.PLACIDUS
    zodiac_system: ZodiacSystem = ZodiacSystem.TROPICAL
    ayanamsa: Optional[float] = None


class PlanetaryPosition(BaseModel):
    """Represents the detailed position of a single celestial body."""
    planet: str
    sign: str
    degree: float
    house: Optional[int] = None
    retrograde: bool = False

