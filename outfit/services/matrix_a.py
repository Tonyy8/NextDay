"""Matrix A — เกณฑ์มาตรฐานจาก Simple Table + สภาพอากาศ."""

from __future__ import annotations

from dataclasses import dataclass

from outfit.models import DressRule, Location
from outfit.services.weather import Weather


@dataclass
class MatrixA:
    location: Location
    weather: Weather
    rule: DressRule
    allowed_styles: list[str]
    forbidden_rules: list[str]
    formality_min: float


def build_matrix_a(location_slug: str, weather: Weather) -> MatrixA:
    loc = Location.objects.get(slug=location_slug)
    rule = (
        DressRule.objects.filter(
            location=loc,
            temp_min__lte=weather.temp_c,
            temp_max__gte=weather.temp_c,
        ).first()
    )
    if not rule:
        rule = DressRule.objects.filter(location=loc).first()
    if not rule:
        raise ValueError(f"no dress rules for location: {location_slug}")

    return MatrixA(
        location=loc,
        weather=weather,
        rule=rule,
        allowed_styles=list(rule.allowed_styles),
        forbidden_rules=list(rule.forbidden_rules),
        formality_min=rule.formality_min,
    )
