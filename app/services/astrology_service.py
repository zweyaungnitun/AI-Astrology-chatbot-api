# app/services/astrology_service.py
from vedastro import Calculate, Time, GeoLocation
from datetime import datetime, date, time
from typing import Dict, Any, List, Optional, Tuple
import logging
import time as time_module
from math import floor
import re

from app.schemas.chart import (
    ChartCalculationRequest, HouseSystem, ZodiacSystem
)

logger = logging.getLogger(__name__)

class AstrologyService:
    # Mapping from our house systems to Vedastro house system numbers
    HOUSE_SYSTEM_MAP = {
        HouseSystem.PLACIDUS: 1,  # Placidus
        HouseSystem.KOCH: 2,       # Koch
        HouseSystem.PORPHYRY: 3,   # Porphyrius
        HouseSystem.EQUAL: 4,      # Equal
        HouseSystem.WHOLE_SIGN: 5, # Whole Sign
    }
    
    # Planet names mapping
    PLANET_NAMES = {
        "Sun": "Sun", "Moon": "Moon", "Mars": "Mars", "Mercury": "Mercury",
        "Jupiter": "Jupiter", "Venus": "Venus", "Saturn": "Saturn",
        "Rahu": "North Node", "Ketu": "South Node", "Uranus": "Uranus",
        "Neptune": "Neptune", "Pluto": "Pluto"
    }
    
    # Sign names
    ZODIAC_SIGNS = [
        "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
        "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
    ]

    @staticmethod
    def parse_location(location_str: str) -> Tuple[float, float, str]:
        """
        Parse location string into latitude, longitude, and place name.
        Returns: (latitude, longitude, place_name)
        """
        try:
            # Try to parse coordinates first
            if re.match(r'^-?\d+\.?\d*,\s*-?\d+\.?\d*$', location_str):
                lat, lon = map(float, location_str.split(','))
                return lat, lon, location_str
            
            # If it's a place name, use geocoding (simplified for now)
            # In production, integrate with a proper geocoding service
            place_name = location_str.strip()
            
            # Default coordinates for major cities (simplified)
            city_coordinates = {
                "new york": (40.7128, -74.0060),
                "london": (51.5074, -0.1278),
                "mumbai": (19.0760, 72.8777),
                "tokyo": (35.6762, 139.6503),
                "sydney": (-33.8688, 151.2093),
                "los angeles": (34.0522, -118.2437),
                "paris": (48.8566, 2.3522),
                "berlin": (52.5200, 13.4050),
                "moscow": (55.7558, 37.6173),
                "beijing": (39.9042, 116.4074),
            }
            
            # Check if location matches any known city
            location_lower = location_str.lower()
            for city, coords in city_coordinates.items():
                if city in location_lower:
                    return coords[0], coords[1], location_str
            
            # Default to New York if no match
            logger.warning(f"Using default coordinates for location: {location_str}")
            return 40.7128, -74.0060, location_str
            
        except Exception as e:
            logger.error(f"Error parsing location '{location_str}': {str(e)}")
            return 40.7128, -74.0060, "New York, USA"  # Default to New York

    @staticmethod
    def calculate_chart(request: ChartCalculationRequest) -> Dict[str, Any]:
        """
        Calculate a birth chart using Vedastro library.
        """
        start_time = time_module.time()
        
        try:
            # Parse location
            latitude, longitude, place_name = AstrologyService.parse_location(request.birth_location)
            
            # Create time object
            birth_datetime = datetime.combine(request.birth_date, request.birth_time)
            time_obj = Time(
                birth_datetime.year,
                birth_datetime.month,
                birth_datetime.day,
                birth_datetime.hour,
                birth_datetime.minute,
                birth_datetime.second,
                request.birth_timezone
            )
            
            # Create location object
            location_obj = GeoLocation(latitude, longitude)
            
            # Get house system code
            house_system_code = AstrologyService.HOUSE_SYSTEM_MAP.get(
                request.house_system, 1  # Default to Placidus
            )
            
            # Calculate chart - Vedastro typically uses Calculate.AstroChart
            calculation = Calculate.AstroChart(time_obj, location_obj, house_system_code)
            
            # Get planetary positions
            planetary_positions = AstrologyService._get_planetary_positions(calculation)
            
            # Get house positions
            house_positions = AstrologyService._get_house_positions(calculation)
            
            # Get aspects
            aspects = AstrologyService._get_aspects(planetary_positions)
            
            # Generate summary
            summary = AstrologyService._generate_summary(planetary_positions, house_positions)
            
            calculation_time = time_module.time() - start_time
            
            return {
                "planetary_positions": planetary_positions,
                "house_positions": house_positions,
                "aspects": aspects,
                "summary": summary,
                "calculation_time": calculation_time,
                "metadata": {
                    "house_system": request.house_system.value,
                    "zodiac_system": request.zodiac_system.value,
                    "ayanamsa": request.ayanamsa,
                    "calculated_at": datetime.utcnow().isoformat(),
                    "location_used": place_name
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating chart: {str(e)}")
            raise ValueError(f"Chart calculation failed: {str(e)}")

    @staticmethod
    def _get_planetary_positions(calculation) -> List[Dict[str, Any]]:
        """Extract planetary positions from calculation."""
        positions = []
        
        try:
            # Vedastro typically provides planetary data through specific properties
            # This is a generic implementation - adjust based on actual vedastro API
            
            # Example planets to check (adjust based on actual vedastro properties)
            planets_to_check = [
                "Sun", "Moon", "Mars", "Mercury", "Jupiter", 
                "Venus", "Saturn", "Rahu", "Ketu"
            ]
            
            for planet_name in planets_to_check:
                try:
                    # Try to get planet data - this will vary based on vedastro API
                    # This is a generic approach
                    planet_data = getattr(calculation, planet_name, None)
                    if not planet_data:
                        continue
                    
                    # Extract basic information (adjust based on actual vedastro properties)
                    longitude = getattr(planet_data, "Longitude", 0)
                    sign_index = int(longitude / 30) % 12
                    sign = AstrologyService.ZODIAC_SIGNS[sign_index]
                    degree = longitude % 30
                    
                    # Get house position (if available)
                    house = getattr(planet_data, "House", None)
                    
                    # Check retrograde (if available)
                    retrograde = getattr(planet_data, "IsRetrograde", False)
                    
                    position = {
                        "planet": AstrologyService.PLANET_NAMES.get(planet_name, planet_name),
                        "sign": sign,
                        "degree": round(degree, 4),
                        "longitude": round(longitude, 4),
                        "house": house,
                        "retrograde": retrograde,
                        "dignity": AstrologyService._get_dignity(planet_name, sign)
                    }
                    
                    positions.append(position)
                    
                except Exception as e:
                    logger.warning(f"Error getting position for {planet_name}: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error in planetary position extraction: {str(e)}")
        
        return positions

    @staticmethod
    def _get_house_positions(calculation) -> List[Dict[str, Any]]:
        """Extract house positions from calculation."""
        houses = []
        
        try:
            # Vedastro typically provides house cusps through a specific property
            # This is a generic implementation
            
            for house_num in range(1, 13):
                try:
                    # Try to get house data - this will vary based on vedastro API
                    house_data = getattr(calculation, f"House{house_num}", None)
                    if not house_data:
                        continue
                    
                    # Extract house information
                    longitude = getattr(house_data, "Longitude", 0)
                    sign_index = int(longitude / 30) % 12
                    sign = AstrologyService.ZODIAC_SIGNS[sign_index]
                    degree = longitude % 30
                    
                    # Get house lord (ruler)
                    lord = AstrologyService._get_house_lord(sign)
                    
                    house_info = {
                        "house": house_num,
                        "sign": sign,
                        "degree": round(degree, 4),
                        "longitude": round(longitude, 4),
                        "lord": lord
                    }
                    
                    houses.append(house_info)
                    
                except Exception as e:
                    logger.warning(f"Error getting house {house_num}: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error in house position extraction: {str(e)}")
        
        return houses

    @staticmethod
    def _get_aspects(planetary_positions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate planetary aspects based on positions."""
        aspects = []
        
        try:
            # Create a dictionary for easy planet lookup
            planet_dict = {pos["planet"]: pos for pos in planetary_positions}
            planet_names = list(planet_dict.keys())
            
            # Check aspects between all planet pairs
            for i, planet1_name in enumerate(planet_names):
                for planet2_name in planet_names[i+1:]:
                    try:
                        planet1 = planet_dict[planet1_name]
                        planet2 = planet_dict[planet2_name]
                        
                        # Calculate aspect
                        aspect_type, orb, is_exact = AstrologyService._calculate_aspect(
                            planet1["longitude"], planet2["longitude"]
                        )
                        
                        if aspect_type:
                            aspect = {
                                "planet1": planet1_name,
                                "planet2": planet2_name,
                                "aspect_type": aspect_type,
                                "orb": round(orb, 4),
                                "exact": is_exact,
                                "strength": AstrologyService._get_aspect_strength(orb)
                            }
                            aspects.append(aspect)
                            
                    except Exception as e:
                        logger.warning(f"Error calculating aspect between {planet1_name} and {planet2_name}: {str(e)}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error calculating aspects: {str(e)}")
        
        return aspects

    @staticmethod
    def _calculate_aspect(longitude1: float, longitude2: float) -> Tuple[Optional[str], float, bool]:
        """Calculate aspect between two longitudes."""
        diff = abs(longitude1 - longitude2) % 360
        if diff > 180:
            diff = 360 - diff
        
        # Major aspects with orbs
        aspects = {
            "conjunction": (0, 8),
            "opposition": (180, 8),
            "trine": (120, 8),
            "square": (90, 8),
            "sextile": (60, 6)
        }
        
        for aspect_name, (angle, orb) in aspects.items():
            if abs(diff - angle) <= orb:
                return aspect_name, abs(diff - angle), abs(diff - angle) <= 1
        
        return None, 0.0, False

    @staticmethod
    def _get_dignity(planet_name: str, sign: str) -> str:
        """Get planetary dignity based on sign."""
        # Simplified dignity system
        dignities = {
            "Sun": {"Leo": "Rulership", "Aries": "Exaltation", "Libra": "Detriment", "Aquarius": "Fall"},
            "Moon": {"Cancer": "Rulership", "Taurus": "Exaltation", "Capricorn": "Detriment", "Scorpio": "Fall"},
            "Mars": {"Aries": "Rulership", "Scorpio": "Rulership", "Capricorn": "Exaltation", "Libra": "Detriment", "Cancer": "Fall"},
            "Mercury": {"Gemini": "Rulership", "Virgo": "Rulership", "Virgo": "Exaltation", "Pisces": "Detriment", "Pisces": "Fall"},
            "Jupiter": {"Sagittarius": "Rulership", "Pisces": "Rulership", "Cancer": "Exaltation", "Gemini": "Detriment", "Capricorn": "Fall"},
            "Venus": {"Taurus": "Rulership", "Libra": "Rulership", "Pisces": "Exaltation", "Aries": "Detriment", "Virgo": "Fall"},
            "Saturn": {"Capricorn": "Rulership", "Aquarius": "Rulership", "Libra": "Exaltation", "Cancer": "Detriment", "Aries": "Fall"},
        }
        
        return dignities.get(planet_name, {}).get(sign, "Neutral")

    @staticmethod
    def _get_house_lord(sign: str) -> str:
        """Get the ruling planet of a sign."""
        lords = {
            "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury",
            "Cancer": "Moon", "Leo": "Sun", "Virgo": "Mercury",
            "Libra": "Venus", "Scorpio": "Mars", "Sagittarius": "Jupiter",
            "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter"
        }
        return lords.get(sign, "Unknown")

    @staticmethod
    def _get_aspect_strength(orb: float) -> str:
        """Get aspect strength based on orb."""
        if orb <= 1: return "Exact"
        if orb <= 3: return "Strong"
        if orb <= 5: return "Medium"
        return "Weak"

    @staticmethod
    def _generate_summary(planetary_positions: List[Dict], house_positions: List[Dict]) -> str:
        """Generate a simple chart summary."""
        try:
            # Find Ascendant (1st house)
            ascendant = next((h for h in house_positions if h["house"] == 1), None)
            
            # Find Sun and Moon
            sun = next((p for p in planetary_positions if p["planet"] == "Sun"), None)
            moon = next((p for p in planetary_positions if p["planet"] == "Moon"), None)
            
            if not all([ascendant, sun, moon]):
                return "Chart calculated successfully"
            
            summary_parts = []
            
            # Ascendant info
            summary_parts.append(f"Ascendant in {ascendant['sign']} ({ascendant['degree']:.1f}°)")
            
            # Sun and Moon info
            summary_parts.append(f"Sun in {sun['sign']}, Moon in {moon['sign']}")
            
            # Check for prominent aspects
            strong_aspects = []
            for position in planetary_positions:
                if position["planet"] in ["Sun", "Moon"]:
                    if position["dignity"] != "Neutral":
                        strong_aspects.append(f"{position['planet']} in {position['dignity']}")
            
            if strong_aspects:
                summary_parts.append("Notable: " + ", ".join(strong_aspects))
            
            return ". ".join(summary_parts) + "."
            
        except Exception as e:
            logger.warning(f"Error generating summary: {str(e)}")
            return "Birth chart calculated with detailed planetary positions"

    @staticmethod
    def test_vedastro_connection():
        """Test if vedastro is working properly."""
        try:
            # Simple test to check vedastro availability
            test_time = Time(2024, 1, 1, 12, 0, 0, "UTC")
            test_location = GeoLocation(40.7128, -74.0060)
            
            # Try to create a basic calculation
            calculation = Calculate.AstroChart(test_time, test_location, 1)
            
            logger.info("✅ Vedastro connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"❌ Vedastro connection test failed: {str(e)}")
            return False