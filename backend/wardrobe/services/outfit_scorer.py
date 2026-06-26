"""Outfit scoring — Matrix A (สถานที่) × Matrix B (ตู้เสื้อผ้า) → 3 ชุดที่ดีที่สุด."""

from __future__ import annotations

from dataclasses import dataclass

from database.models import BOTTOM_TYPES, TOP_TYPES

from .color_utils import lab_distance, thai_color_name
from .destination_profiles import (
    DEFAULT_FABRIC_THICKNESS,
    STYLE_LABELS,
    WEATHER_LABELS,
    WEATHER_THICKNESS_SCORE,
    MatrixA,
    build_matrix_a,
)
from .outfit_engine import ColorMatcher, OutfitSuggestion

WEIGHT_CORRECTNESS = 0.40
WEIGHT_WEATHER = 0.20
WEIGHT_COLOR = 0.40


@dataclass
class MatrixB:
    pk: int
    garment_type: str
    part: str
    formality: int
    fabric_thickness: str
    lab_l: float
    lab_a: float
    lab_b: float
    primary_color_hex: str
    color_name_th: str
    raw: object


def build_matrix_b(item) -> MatrixB:
    thickness = getattr(item, "fabric_thickness", None) or DEFAULT_FABRIC_THICKNESS.get(
        item.garment_type, "medium"
    )
    return MatrixB(
        pk=item.pk,
        garment_type=item.garment_type,
        part=item.part,
        formality=item.formality,
        fabric_thickness=thickness,
        lab_l=item.lab_l,
        lab_a=item.lab_a,
        lab_b=item.lab_b,
        primary_color_hex=item.primary_color_hex,
        color_name_th=getattr(item, "color_name_th", "") or "",
        raw=item,
    )


def _color_category(b: MatrixB) -> str:
    """Best-effort base-color name. Prefer the human label (more accurate than the
    crude auto-detector, which e.g. maps beige/cream to 'ส้ม'); fall back to auto."""
    label = (b.color_name_th or "").strip()
    if label:
        return label
    return thai_color_name(b.primary_color_hex)


def passes_hard_filter(b: MatrixB, matrix_a: MatrixA) -> bool:
    if b.garment_type not in matrix_a.allowed_categories:
        return False
    if matrix_a.avoid_colors and _color_category(b) in matrix_a.avoid_colors:
        return False
    rules = matrix_a.garment_rules.get(b.garment_type)
    if not rules:
        return b.formality <= matrix_a.formality_level + 1
    if not (rules["formality_min"] <= b.formality <= rules["formality_max"]):
        return False
    if b.fabric_thickness not in rules["thickness_allowed"]:
        return False
    return True


def score_correctness(b: MatrixB, matrix_a: MatrixA) -> float:
    rules = matrix_a.garment_rules.get(b.garment_type)
    if not rules:
        target = matrix_a.formality_level
        delta = abs(b.formality - target)
    else:
        target = (rules["formality_min"] + rules["formality_max"]) / 2
        delta = abs(b.formality - target)
    return max(0.0, 100.0 - delta * 22.0)


def score_weather(b: MatrixB, weather: str) -> float:
    table = WEATHER_THICKNESS_SCORE.get(weather, WEATHER_THICKNESS_SCORE["mild"])
    return float(table.get(b.fabric_thickness, 50))


def score_color_pair(top: MatrixB, bottom: MatrixB) -> tuple[float, str]:
    delta = lab_distance(top.lab_l, top.lab_a, top.lab_b, bottom.lab_l, bottom.lab_a, bottom.lab_b)
    matcher = ColorMatcher()
    result = matcher.score_pair(top.raw, bottom.raw)
    detail = f"ΔE={delta:.1f}"
    if delta < matcher.settings.lab_min_delta:
        detail += " ใกล้เกินไป"
    elif delta > matcher.settings.lab_max_delta:
        detail += " ห่างเกินไป"
    else:
        detail += " โซนสีเหมาะสม"
    return result.score, detail


class OutfitScoringEngine:
    def suggest_outfits(
        self,
        user_items,
        destination,
        count: int = 3,
        slot_overrides: dict | None = None,
    ) -> list[OutfitSuggestion]:
        matrix_a = build_matrix_a(destination)
        matrix_bs = [build_matrix_b(i) for i in user_items]
        eligible = [b for b in matrix_bs if passes_hard_filter(b, matrix_a)]

        tops = [b for b in eligible if b.part == "top" or b.garment_type in TOP_TYPES]
        bottoms = [b for b in eligible if b.part == "bottom" or b.garment_type in BOTTOM_TYPES]

        pairs: list[OutfitSuggestion] = []
        for top in tops:
            for bottom in bottoms:
                pairs.append(self._score_pair(top, bottom, matrix_a))

        pairs.sort(key=lambda x: x.score, reverse=True)

        results: list[OutfitSuggestion] = []
        used_tops: set[int] = set()
        for pair in pairs:
            if pair.top.pk in used_tops:
                continue
            used_tops.add(pair.top.pk)
            pair.rank = len(results) + 1
            results.append(pair)
            if len(results) >= count:
                break

        if slot_overrides:
            self._apply_overrides(results, slot_overrides, tops, bottoms, matrix_a)

        return results

    def _score_pair(self, top: MatrixB, bottom: MatrixB, matrix_a: MatrixA) -> OutfitSuggestion:
        corr = (score_correctness(top, matrix_a) + score_correctness(bottom, matrix_a)) / 2
        weather = (score_weather(top, matrix_a.weather) + score_weather(bottom, matrix_a.weather)) / 2
        color, color_detail = score_color_pair(top, bottom)

        total = (
            WEIGHT_CORRECTNESS * corr
            + WEIGHT_WEATHER * weather
            + WEIGHT_COLOR * color
        )

        theory = (
            f"ถูกต้อง {corr:.0f}% · อากาศ {weather:.0f}% · สี {color:.0f}%"
        )
        detail = (
            f"{STYLE_LABELS.get(matrix_a.style, matrix_a.style)} / "
            f"{WEATHER_LABELS.get(matrix_a.weather, matrix_a.weather)} · {color_detail}"
        )

        return OutfitSuggestion(
            top=top.raw,
            bottom=bottom.raw,
            score=round(total, 1),
            theory=theory,
            detail=detail,
            correctness_score=round(corr, 1),
            weather_score=round(weather, 1),
            color_score=round(color, 1),
        )

    def _apply_overrides(self, results, overrides, tops, bottoms, matrix_a):
        top_map = {b.pk: b for b in tops}
        bottom_map = {b.pk: b for b in bottoms}
        for idx, slots in overrides.items():
            if idx >= len(results):
                continue
            top_b, bottom_b = None, None
            if "top" in slots and slots["top"] in top_map:
                top_b = top_map[slots["top"]]
                results[idx].top = top_b.raw
            if "bottom" in slots and slots["bottom"] in bottom_map:
                bottom_b = bottom_map[slots["bottom"]]
                results[idx].bottom = bottom_b.raw
            if top_b is None:
                top_b = build_matrix_b(results[idx].top)
            if bottom_b is None:
                bottom_b = build_matrix_b(results[idx].bottom)
            rescored = self._score_pair(top_b, bottom_b, matrix_a)
            results[idx].score = rescored.score
            results[idx].theory = rescored.theory
            results[idx].detail = rescored.detail
            results[idx].correctness_score = rescored.correctness_score
            results[idx].weather_score = rescored.weather_score
            results[idx].color_score = rescored.color_score
