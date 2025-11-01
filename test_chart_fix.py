#!/usr/bin/env python3
"""Test script to verify the chart service fixes."""

import sys
import os
import asyncio
from datetime import date, time
from uuid import uuid4

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.astrology_service import AstrologyService
from app.schemas.chart import ChartCalculationRequest, HouseSystem, ZodiacSystem

async def test_astrology_service():
    """Test the astrology service directly."""
    try:
        print("Testing AstrologyService...")
        
        # Create a test request
        request = ChartCalculationRequest(
            birth_date=date(1990, 1, 1),
            birth_time=time(12, 0, 0),
            birth_location="New York, USA",
            birth_timezone="UTC",
            birth_latitude=40.7128,
            birth_longitude=-74.0060,
            house_system=HouseSystem.PLACIDUS,
            zodiac_system=ZodiacSystem.TROPICAL,
            ayanamsa=0.0
        )
        
        # Create astrology service instance
        astrology_service = AstrologyService()
        
        # Test the calculation
        result = await astrology_service.calculate_chart(request)
        
        if result:
            print("✅ AstrologyService test successful!")
            print(f"Calculation time: {result['calculation_time']:.3f}s")
            print(f"Planetary positions: {len(result['planetary_positions'])}")
            print(f"House positions: {len(result['house_positions'])}")
            print(f"Aspects: {len(result['aspects'])}")
            print(f"Summary: {result['summary']}")
            return True
        else:
            print("❌ AstrologyService test failed - no result")
            return False
            
    except Exception as e:
        print(f"❌ AstrologyService test error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_astrology_service())
    sys.exit(0 if success else 1)
