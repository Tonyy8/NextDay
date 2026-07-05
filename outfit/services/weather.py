"""OpenWeather API — ดึงสภาพอากาศเรียลไทม์."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import urllib.request
import json

logger = logging.getLogger(__name__)


@dataclass
class Weather:
    temp_c: float
    description: str
    is_mock: bool


def fetch_weather(city: str = "Bangkok") -> Weather:
    api_key = os.environ.get("OPENWEATHER_API_KEY", "")
    if not api_key:
        logger.info("No OPENWEATHER_API_KEY — using mock weather")
        return Weather(temp_c=32.0, description="ร้อน (mock)", is_mock=True)

    url = (
        f"https://api.openweathermap.org/data/2.5/weather"
        f"?q={city}&appid={api_key}&units=metric"
    )
    try:
        with urllib.request.urlopen(url, timeout=8) as resp:
            data = json.loads(resp.read().decode())
        return Weather(
            temp_c=float(data["main"]["temp"]),
            description=data["weather"][0]["description"],
            is_mock=False,
        )
    except Exception as e:
        logger.warning("Weather API failed: %s", e)
        return Weather(temp_c=30.0, description="ไม่ทราบ (fallback)", is_mock=True)
