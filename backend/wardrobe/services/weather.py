"""OpenWeather — ดึงสภาพอากาศสำหรับ Dashboard และระบบแนะนำชุด."""

from __future__ import annotations

import json
import logging
import urllib.request
from dataclasses import dataclass
from datetime import datetime

from django.conf import settings

logger = logging.getLogger(__name__)

CITY_LABELS = {
    "Bangkok": "กรุงเทพฯ",
    "Chiang Mai": "เชียงใหม่",
    "Phuket": "ภูเก็ต",
    "Ubon Ratchathani": "อุบลราชธานี",
}

DEFAULT_WEATHER_CITY = "Ubon Ratchathani"

MAIN_TH = {
    "Clear": "ท้องฟ้าแจ่มใส",
    "Clouds": "มีเมฆบางส่วน",
    "Rain": "มีฝนตก",
    "Drizzle": "ฝนปรอย",
    "Thunderstorm": "พายุฝนฟ้าคะนอง",
    "Mist": "หมอก",
    "Fog": "หมอก",
    "Haze": "หมอกควัน",
    "Smoke": "ควัน",
    "Dust": "ฝุ่น",
    "Sand": "ฝุ่นทราย",
    "Ash": "เถ้าถ่าน",
    "Squall": "ลมแรง",
    "Tornado": "พายุทอร์นาโด",
    "Snow": "หิมะ",
}

ICON_MAP = {
    "Clear": "sun",
    "Clouds": "cloud",
    "Rain": "cloud-rain",
    "Drizzle": "cloud-rain",
    "Thunderstorm": "cloud-storm",
    "Mist": "mist",
    "Fog": "mist",
    "Haze": "mist",
}


@dataclass
class Weather:
    temp_c: float
    feels_like_c: float
    description: str
    city: str
    icon: str
    humidity: int
    main: str
    band: str
    is_live: bool

    @property
    def temp_display(self) -> str:
        return f"{round(self.temp_c)}°"

    @property
    def band_label(self) -> str:
        labels = {"hot": "ร้อน", "mild": "อุ่นสบาย", "cool": "เย็น/แอร์"}
        return labels.get(self.band, self.band)


def _band_from_temp(temp_c: float) -> str:
    if temp_c >= 30:
        return "hot"
    if temp_c >= 24:
        return "mild"
    return "cool"


def _resolve_city(city: str | None = None) -> str:
    if city:
        return city
    return getattr(settings, "WEATHER_CITY", DEFAULT_WEATHER_CITY) or DEFAULT_WEATHER_CITY


def _city_label(city: str, api_name: str | None = None) -> str:
    if city in CITY_LABELS:
        return CITY_LABELS[city]
    if api_name:
        for key, label in CITY_LABELS.items():
            if key.lower() == api_name.lower():
                return label
        if "ubon" in api_name.lower():
            return "อุบลราชธานี"
    return CITY_LABELS.get(city, api_name or city)


def _mock_weather(city: str | None = None) -> Weather:
    city = _resolve_city(city)
    hour = datetime.now().hour
    if 6 <= hour < 10:
        temp, main, desc = 28.0, "Clear", "ท้องฟ้าแจ่มใส"
    elif 10 <= hour < 16:
        temp, main, desc = 33.0, "Clouds", "มีเมฆบางส่วน"
    elif 16 <= hour < 19:
        temp, main, desc = 31.0, "Clouds", "อากาศร้อนชื้น"
    else:
        temp, main, desc = 27.0, "Clouds", "อากาศอุ่นสบาย"
    return Weather(
        temp_c=temp,
        feels_like_c=temp + 2,
        description=desc,
        city=_city_label(city),
        icon=ICON_MAP.get(main, "cloud"),
        humidity=68,
        main=main,
        band=_band_from_temp(temp),
        is_live=False,
    )


def fetch_weather(city: str | None = None) -> Weather:
    city = _resolve_city(city)
    api_key = getattr(settings, "OPENWEATHER_API_KEY", "") or ""
    if not api_key:
        return _mock_weather(city)

    url = (
        f"https://api.openweathermap.org/data/2.5/weather"
        f"?q={city},TH&appid={api_key}&units=metric&lang=th"
    )
    try:
        with urllib.request.urlopen(url, timeout=8) as resp:
            data = json.loads(resp.read().decode())
        main = data["weather"][0]["main"]
        temp = float(data["main"]["temp"])
        return Weather(
            temp_c=temp,
            feels_like_c=float(data["main"].get("feels_like", temp)),
            description=MAIN_TH.get(main, data["weather"][0]["description"]),
            city=_city_label(city, data.get("name")),
            icon=ICON_MAP.get(main, "cloud"),
            humidity=int(data["main"].get("humidity", 0)),
            main=main,
            band=_band_from_temp(temp),
            is_live=True,
        )
    except Exception as exc:
        logger.warning("Weather API failed: %s", exc)
        fallback = _mock_weather(city)
        fallback.is_live = False
        return fallback
