"""Outfit scoring — Matrix A (สถานที่) × Matrix B (ตู้เสื้อผ้า) → 3 ชุดที่ดีที่สุด."""

from __future__ import annotations

from dataclasses import dataclass

from database.garment_catalog import get_base_garment_type, is_full_outfit
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
FULL_OUTFIT_COLOR_SCORE = 88.0


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
    base_type = get_base_garment_type(b.garment_type)
    if base_type not in matrix_a.allowed_categories:
        return False
    if matrix_a.avoid_colors and _color_category(b) in matrix_a.avoid_colors:
        return False
    rules = matrix_a.garment_rules.get(base_type)
    if not rules:
        return b.formality <= matrix_a.formality_level + 1
    if not (rules["formality_min"] <= b.formality <= rules["formality_max"]):
        return False
    if b.fabric_thickness not in rules["thickness_allowed"]:
        return False
    return True


def score_correctness(b: MatrixB, matrix_a: MatrixA) -> float:
    base_type = get_base_garment_type(b.garment_type)
    rules = matrix_a.garment_rules.get(base_type)
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

        full_pieces = [b for b in eligible if is_full_outfit(b.garment_type)]
        tops = [
            b for b in eligible
            if (b.part == "top" or b.garment_type in TOP_TYPES)
            and not is_full_outfit(b.garment_type)
        ]
        bottoms = [b for b in eligible if b.part == "bottom" or b.garment_type in BOTTOM_TYPES]

        candidates: list[OutfitSuggestion] = []
        for top in tops:
            for bottom in bottoms:
                candidates.append(self._score_pair(top, bottom, matrix_a))
        for piece in full_pieces:
            candidates.append(self._score_full_outfit(piece, matrix_a))

        candidates.sort(key=lambda x: x.score, reverse=True)

        results: list[OutfitSuggestion] = []
        used_items: set[int] = set()
        for outfit in candidates:
            if outfit.top.pk in used_items:
                continue
            used_items.add(outfit.top.pk)
            outfit.rank = len(results) + 1
            results.append(outfit)
            if len(results) >= count:
                break

        if slot_overrides:
            self._apply_overrides(
                results, slot_overrides, tops, bottoms, full_pieces, matrix_a, user_items
            )

        return results

    @staticmethod
    def _lookup_matrix_b(pk, user_items, top_map, bottom_map, full_map):
        if pk in full_map:
            return full_map[pk]
        if pk in top_map:
            return top_map[pk]
        if pk in bottom_map:
            return bottom_map[pk]
        for item in user_items:
            if item.pk == pk:
                return build_matrix_b(item)
        return None

    def _apply_overrides(self, results, overrides, tops, bottoms, full_pieces, matrix_a, user_items):
        top_map = {b.pk: b for b in tops}
        bottom_map = {b.pk: b for b in bottoms}
        full_map = {b.pk: b for b in full_pieces}
        for idx, slots in overrides.items():
            if idx >= len(results):
                continue
            top_pk = slots.get("top")
            bottom_pk = slots.get("bottom")

            if top_pk and not bottom_pk:
                top_b = self._lookup_matrix_b(top_pk, user_items, top_map, bottom_map, full_map)
                if top_b and is_full_outfit(top_b.garment_type):
                    rescored = self._score_full_outfit(top_b, matrix_a)
                    rescored.rank = results[idx].rank
                    results[idx] = rescored
                    continue

            top_b = (
                self._lookup_matrix_b(top_pk, user_items, top_map, bottom_map, full_map)
                if top_pk else None
            )
            bottom_b = (
                self._lookup_matrix_b(bottom_pk, user_items, top_map, bottom_map, full_map)
                if bottom_pk else None
            )

            if top_b is None:
                top_b = build_matrix_b(results[idx].top)
            if bottom_b is None and not results[idx].is_full_outfit:
                bottom_b = build_matrix_b(results[idx].bottom)

            if top_b and is_full_outfit(top_b.garment_type) and not bottom_b:
                rescored = self._score_full_outfit(top_b, matrix_a)
            elif top_b and bottom_b:
                rescored = self._score_pair(top_b, bottom_b, matrix_a)
            else:
                continue

            rescored.rank = results[idx].rank
            results[idx] = rescored

    def _score_full_outfit(self, piece: MatrixB, matrix_a: MatrixA) -> OutfitSuggestion:
        corr = score_correctness(piece, matrix_a)
        weather = score_weather(piece, matrix_a.weather)
        color = FULL_OUTFIT_COLOR_SCORE

        total = (
            WEIGHT_CORRECTNESS * corr
            + WEIGHT_WEATHER * weather
            + WEIGHT_COLOR * color
        )

        theory = f"ถูกต้อง {corr:.0f}% · อากาศ {weather:.0f}% · ชุดเซ็ต"
        detail = (
            f"{STYLE_LABELS.get(matrix_a.style, matrix_a.style)} / "
            f"{WEATHER_LABELS.get(matrix_a.weather, matrix_a.weather)} · "
            "ชุดชิ้นเดียว ไม่ต้องจับคู่ท่อนบน/ล่าง"
        )

        return OutfitSuggestion(
            top=piece.raw,
            bottom=None,
            score=round(total, 1),
            theory=theory,
            detail=detail,
            correctness_score=round(corr, 1),
            weather_score=round(weather, 1),
            color_score=round(color, 1),
            is_full_outfit=True,
        )

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
            is_full_outfit=False,
        )
