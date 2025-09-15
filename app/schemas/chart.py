# app/schemas/chart.py
from sqlmodel import SQLModel, Field, Column, JSON
from typing import Optional, Dict, Any, List
from datetime import datetime, date, time
from uuid import UUID, uuid4
from enum import Enum
from pydantic import validator

class ChartType(str, Enum):
    BIRTH_CHART = "birth_chart"
    SOLAR_RETURN = "solar_return"
    LUNAR_RETURN = "lunar_return"
    TRANSIT = "transit"
    SYNATRY = "synatry"

class HouseSystem(str, Enum):
    PLACIDUS = "placidus"
    KOCH = "koch"
    PORPHYRY = "porphyry"
    EQUAL = "equal"
    WHOLE_SIGN = "whole_sign"

class ZodiacSystem(str, Enum):
    TROPICAL = "tropical"
    SIDEREAL = "sidereal"

class ChartBase(SQLModel):
    user_id: UUID = Field(foreign_key="user.id", description="User who owns this chart")
    chart_type: ChartType = Field(default=ChartType.BIRTH_CHART)
    chart_name: Optional[str] = Field(default="Birth Chart", description="Custom name for the chart")
    
    # Birth data
    birth_date: date = Field(..., description="Date of birth")
    birth_time: time = Field(..., description="Time of birth")
    birth_location: str = Field(..., description="Birth location (e.g., 'New York, USA')")
    birth_timezone: str = Field(default="UTC", description="Timezone of birth")
    
    # Calculation settings
    house_system: HouseSystem = Field(default=HouseSystem.PLACIDUS)
    zodiac_system: ZodiacSystem = Field(default=ZodiacSystem.TROPICAL)
    ayanamsa: Optional[float] = Field(default=0.0, description="Ayanamsa value for sidereal zodiac")

class Chart(ChartBase, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    
    # Calculated chart data
    planetary_positions: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Planetary positions and aspects"
    )
    house_positions: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="House cusps and positions"
    )
    aspects: List[Dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSON),
        description="Planetary aspects"
    )
    summary: Optional[str] = Field(default=None, description="Auto-generated chart summary")
    
    # Metadata
    is_primary: bool = Field(default=False, description="Is this the user's primary chart")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    calculation_time: Optional[float] = Field(default=None, description="Time taken to calculate (seconds)")

class ChartCreate(ChartBase):
    pass

class ChartUpdate(SQLModel):
    chart_name: Optional[str] = None
    is_primary: Optional[bool] = None

class ChartResponse(SQLModel):
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
    calculation_time: Optional[float]

class ChartCalculationRequest(SQLModel):
    birth_date: date
    birth_time: time
    birth_location: str
    birth_timezone: str = "UTC"
    house_system: HouseSystem = HouseSystem.PLACIDUS
    zodiac_system: ZodiacSystem = ZodiacSystem.TROPICAL
    ayanamsa: Optional[float] = None

class PlanetaryPosition(SQLModel):
    planet: str
    sign: str
    degree: float
    house: Optional[int] = None
    nakshatra: Optional[str] = None
    nakshatra_lord: Optional[str] = None
    dignity: Optional[str] = None
    retrograde: bool = False

class HousePosition(SQLModel):
    house: int
    sign: str
    degree: float
    lord: str

class Aspect(SQLModel):
    planet1: str
    planet2: str
    aspect_type: str
    orb: float
    exact: bool
