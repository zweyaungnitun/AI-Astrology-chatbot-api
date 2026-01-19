from sqlmodel import SQLModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, date, time
from uuid import UUID

# Import the enums from the new model file to ensure consistency
from app.models.chart import ChartType, HouseSystem, ZodiacSystem

# --- Base Schema ---
# This contains fields common to chart creation.
class ChartBase(SQLModel):
    # user_id is included here to match the CRUD function's expectation.
    # In a real API, this would likely be sourced from the authenticated user token.
    user_id: UUID
    chart_type: ChartType = Field(default=ChartType.BIRTH_CHART)
    chart_name: Optional[str] = Field(default="Birth Chart", description="Custom name for the chart")
    birth_date: date
    birth_time: time
    birth_location: str
    birth_timezone: str = "UTC"
    birth_latitude: Optional[float] = Field(default=None, description="Latitude. If not provided, will be parsed from birth_location")
    birth_longitude: Optional[float] = Field(default=None, description="Longitude. If not provided, will be parsed from birth_location")
    house_system: HouseSystem = Field(default=HouseSystem.PLACIDUS)
    zodiac_system: ZodiacSystem = Field(default=ZodiacSystem.TROPICAL)
    ayanamsa: Optional[float] = Field(default=0.0)
    is_primary: Optional[bool] = Field(default=False, description="Set this chart as the user's primary one.")

# --- Input Schemas ---

class ChartCreate(ChartBase):
    """Schema for creating a new chart. Inherits all fields from ChartBase."""
    pass

class ChartUpdate(SQLModel):
    """Schema for updating a chart's name or primary status."""
    chart_name: Optional[str] = None
    is_primary: Optional[bool] = None

# --- Output Schemas ---

class ChartResponse(SQLModel):
    """Schema for returning a full chart object in an API response."""
    id: UUID
    user_id: UUID
    chart_type: ChartType
    chart_name: Optional[str]
    birth_date: date
    birth_time: time
    birth_location: str
    birth_timezone: str
    house_system: HouseSystem
    zodiac_system: ZodiacSystem
    planetary_positions: Dict[str, Any]
    house_positions: Dict[str, Any]
    aspects: List[Dict[str, Any]]
    summary: Optional[str]
    is_primary: bool
    created_at: datetime
    updated_at: datetime
    calculation_time: Optional[float]

# --- Service/Utility Schemas ---

class ChartCalculationRequest(SQLModel):
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


class PlanetaryPosition(SQLModel):
    """Represents the detailed position of a single celestial body."""
    planet: str
    sign: str
    degree: float
    house: Optional[int] = None
    retrograde: bool = False

class HousePosition(SQLModel):
    """Represents a single house cusp in the chart."""
    house: int
    sign: str
    degree: float
    lord: str

class Aspect(SQLModel):
    """Represents an aspect between two celestial bodies."""
    planet1: str
    planet2: str
    aspect_type: str
    orb: float
    exact: bool
