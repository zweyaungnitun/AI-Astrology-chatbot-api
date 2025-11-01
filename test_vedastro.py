#!/usr/bin/env python3
"""Test script to understand vedastro Time constructor."""

from vedastro import Time, GeoLocation, Calculate
from datetime import datetime

print("Testing vedastro Time constructor...")

try:
    # Test different Time constructor signatures
    print("Testing Time(year, month, day, hour, minute, second, timezone)...")
    time_obj = Time(2024, 1, 1, 12, 0, 0, "UTC")
    print("✅ Success with 7 parameters")
except Exception as e:
    print(f"❌ Failed with 7 parameters: {e}")

try:
    print("Testing Time(year, month, day, hour, minute, second)...")
    time_obj = Time(2024, 1, 1, 12, 0, 0)
    print("✅ Success with 6 parameters")
except Exception as e:
    print(f"❌ Failed with 6 parameters: {e}")

try:
    print("Testing Time(datetime)...")
    dt = datetime(2024, 1, 1, 12, 0, 0)
    time_obj = Time(dt)
    print("✅ Success with datetime object")
except Exception as e:
    print(f"❌ Failed with datetime object: {e}")

try:
    print("Testing Time(datetime, timezone)...")
    dt = datetime(2024, 1, 1, 12, 0, 0)
    time_obj = Time(dt, "UTC")
    print("✅ Success with datetime and timezone")
except Exception as e:
    print(f"❌ Failed with datetime and timezone: {e}")

# Test GeoLocation
try:
    print("Testing GeoLocation(lat, lon)...")
    location = GeoLocation(40.7128, -74.0060)
    print("✅ GeoLocation success")
except Exception as e:
    print(f"❌ GeoLocation failed: {e}")

# Test Calculate.AstroChart
try:
    print("Testing Calculate.AstroChart...")
    time_obj = Time(2024, 1, 1, 12, 0, 0)
    location = GeoLocation(40.7128, -74.0060)
    chart = Calculate.AstroChart(time_obj, location, 1)
    print("✅ Calculate.AstroChart success")
except Exception as e:
    print(f"❌ Calculate.AstroChart failed: {e}")
