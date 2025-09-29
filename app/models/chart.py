from sqlmodel import SQLModel, Field, Column, JSON, Relationship
from typing import Optional, Dict, Any, List
from datetime import datetime, date, time
from uuid import UUID, uuid4
from enum import Enum

# Enums define the allowed values for specific fields in the database.
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

class Chart(SQLModel, table=True):
    """
    Represents the 'chart' table in the database.
    This is the internal, source-of-truth representation of a chart.
    """
    __tablename__ = "chart"

    # Core Identifiers
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True, description="The user who owns this chart")
    
    # Chart Metadata
    chart_type: ChartType = Field(default=ChartType.BIRTH_CHART)
    chart_name: Optional[str] = Field(default="Birth Chart", description="Custom name for the chart")
    is_primary: bool = Field(default=False, description="Is this the user's primary chart")

    # Core Birth Data Inputs
    birth_date: date = Field(description="Date of birth")
    birth_time: time = Field(description="Time of birth")
    birth_location: str = Field(description="Birth location (e.g., 'New York, USA')")
    birth_timezone: str = Field(default="UTC", description="Timezone of birth")
    
    # Astrological Calculation Settings
    house_system: HouseSystem = Field(default=HouseSystem.PLACIDUS)
    zodiac_system: ZodiacSystem = Field(default=ZodiacSystem.TROPICAL)
    ayanamsa: Optional[float] = Field(default=0.0, description="Ayanamsa value for sidereal zodiac")

    # Calculated Chart Data (stored as JSON)
    planetary_positions: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    house_positions: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    aspects: List[Dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    summary: Optional[str] = Field(default=None, description="AI-generated chart summary")
    
    # Timestamps & Performance
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    calculation_time: Optional[float] = Field(default=None, description="Time taken to calculate (seconds)")

    # To enable this relationship, the User model needs a 'charts' field.
    # user: Optional["User"] = Relationship(back_populates="charts")
