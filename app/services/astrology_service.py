import logging
import re
import time
from datetime import datetime
from typing import Dict, Any, List, Tuple

from app.schemas.chart import ChartCalculationRequest, HouseSystem

logger = logging.getLogger(__name__)


class AstrologyService:
    """Deterministic astrology calculation for testing purposes."""

    PLANETS = [
        "Sun", "Moon", "Mercury", "Venus", "Mars",
        "Jupiter", "Saturn", "Rahu", "Ketu", "Uranus",
        "Neptune", "Pluto"
    ]

    ZODIAC_SIGNS = [
        "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
        "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
    ]

    HOUSE_SYSTEM_MAP = {
        HouseSystem.PLACIDUS: "placidus",
        HouseSystem.KOCH: "koch",
        HouseSystem.PORPHYRY: "porphyry",
        HouseSystem.EQUAL: "equal",
        HouseSystem.WHOLE_SIGN: "whole_sign",
    }

    async def calculate_chart(self, request: ChartCalculationRequest) -> Dict[str, Any]:
        start_time = time.time()
        lat = getattr(request, "birth_latitude", None)
        lon = getattr(request, "birth_longitude", None)

        if lat is None or lon is None:
            lat, lon, place_name = self.parse_location(request.birth_location)
        else:
            place_name = request.birth_location or f"{lat},{lon}"

        birth_dt = datetime.combine(request.birth_date, request.birth_time)
        epoch_sec = int(birth_dt.timestamp())

        planetary_positions = []
        for i, planet in enumerate(self.PLANETS):
            seed = (epoch_sec // 60) + i * 137 + int((lat or 0) * 1000) + int((lon or 0) * 1000)
            if request.ayanamsa:
                seed += int(request.ayanamsa * 100)
            longitude = (seed % 36000) / 100.0
            sign_index = int(longitude // 30) % 12
            degree = longitude % 30
            house = (int(longitude // 30) + 1) % 12 or 12
            retrograde = (seed % 17 == 0)

            planetary_positions.append({
                "planet": planet,
                "sign": self.ZODIAC_SIGNS[sign_index],
                "degree": round(degree, 4),
                "longitude": round(longitude, 4),
                "house": house,
                "retrograde": retrograde
            })

        # Ascendant and houses
        asc_seed = (epoch_sec // 3600 + int((lat or 0) * 10) + int((lon or 0) * 10)) % 36000
        asc_long = (asc_seed / 100.0) % 360
        house_positions = []
        for h in range(12):
            cusp_long = (asc_long + h * 30) % 360
            sign_index = int(cusp_long // 30) % 12
            degree = cusp_long % 30
            house_positions.append({
                "house": h + 1,
                "sign": self.ZODIAC_SIGNS[sign_index],
                "degree": round(degree, 4),
                "longitude": round(cusp_long, 4)
            })

        aspects = self._get_aspects(planetary_positions)
        summary = self._generate_summary(planetary_positions, house_positions)

        return {
            "planetary_positions": planetary_positions,
            "house_positions": house_positions,
            "aspects": aspects,
            "summary": summary,
            "calculation_time": round(time.time() - start_time, 4),
            "metadata": {
                "house_system": getattr(request.house_system, "value", None) if request.house_system else None,
                "zodiac_system": getattr(request.zodiac_system, "value", None) if request.zodiac_system else None,
                "ayanamsa": getattr(request, "ayanamsa", None),
                "calculated_at": datetime.utcnow().isoformat(),
                "location_used": place_name
            }
        }

    @staticmethod
    def parse_location(location_str: str) -> Tuple[float, float, str]:
        if not location_str:
            return 40.7128, -74.0060, "New York, USA"
        if re.match(r'^\s*-?\d+(\.\d+)?\s*,\s*-?\d+(\.\d+)?\s*$', location_str):
            lat_s, lon_s = location_str.split(',')
            return float(lat_s), float(lon_s), location_str.strip()
        lookup = {
            "new york": (40.7128, -74.0060),
            "london": (51.5074, -0.1278),
            "mumbai": (19.0760, 72.8777),
            "tokyo": (35.6762, 139.6503),
            "sydney": (-33.8688, 151.2093)
        }
        key = location_str.strip().lower()
        return lookup.get(key, (40.7128, -74.0060))[0], lookup.get(key, (40.7128, -74.0060))[1], location_str

    def _get_aspects(self, positions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        aspects = []
        angles = {"conjunction": 0, "opposition": 180, "trine": 120, "square": 90, "sextile": 60}
        orbs = {"conjunction": 8, "opposition": 8, "trine": 8, "square": 8, "sextile": 6}

        n = len(positions)
        for i in range(n):
            for j in range(i + 1, n):
                diff = abs(positions[i]["longitude"] - positions[j]["longitude"]) % 360
                if diff > 180:
                    diff = 360 - diff
                for name, angle in angles.items():
                    delta = abs(diff - angle)
                    if delta <= orbs[name]:
                        aspects.append({
                            "planet1": positions[i]["planet"],
                            "planet2": positions[j]["planet"],
                            "aspect_type": name,
                            "orb": round(delta, 4),
                            "exact": delta <= 1
                        })
                        break
        return aspects

    def _generate_summary(self, positions: List[Dict[str, Any]], houses: List[Dict[str, Any]]) -> str:
        asc = next((h for h in houses if h["house"] == 1), None)
        sun = next((p for p in positions if p["planet"] == "Sun"), None)
        moon = next((p for p in positions if p["planet"] == "Moon"), None)

        parts = []
        if asc:
            parts.append(f"Ascendant in {asc['sign']} ({asc['degree']:.1f}°)")
        if sun:
            parts.append(f"Sun in {sun['sign']}")
        if moon:
            parts.append(f"Moon in {moon['sign']}")
        return ". ".join(parts) + "." if parts else "Chart calculated successfully."
