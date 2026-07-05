"""Color harmony + CBF + Weighted Sum recommendation engine."""

from __future__ import annotations

import colorsys
from dataclasses import dataclass

from outfit.constants import CBF_WEIGHT, COLOR_WEIGHT, GARMENT_BOTTOM, GARMENT_TOP, TOP_N
from outfit.models import Clothing
from outfit.services.matrix_a import MatrixA


@dataclass
class OutfitPair:
    top: Clothing
    bottom: Clothing
    cbf_score: float
    color_score: float
    total_score: float
    total_percent: int


def _hex_to_hsv(hex_color: str) -> tuple[float, float, float]:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255
    return colorsys.rgb_to_hsv(r, g, b)


def color_harmony_score(top: Clothing, bottom: Clothing) -> float:
    """
    Score_Color(t,b) — ทฤษฎีสีแฟชั่นแบบง่าย:
    - โทนใกล้กัน / complementary / neutral pairing
    """
    h1, s1, v1 = _hex_to_hsv(top.dominant_color_hex)
    h2, s2, v2 = _hex_to_hsv(bottom.dominant_color_hex)

    hue_diff = abs(h1 - h2)
    hue_diff = min(hue_diff, 1 - hue_diff)

    score = 0.5
    # neutral + anything
    if v1 < 0.25 or v2 < 0.25 or v1 > 0.85 or v2 > 0.85:
        score += 0.2
    # analogous (hue close)
    if hue_diff < 0.08:
        score += 0.25
    # complementary
    elif 0.4 <= hue_diff <= 0.6:
        score += 0.3
    # clash penalty
    if s1 > 0.7 and s2 > 0.7 and hue_diff < 0.15:
        score -= 0.15

    return round(max(0.0, min(1.0, score)), 3)


def outfit_cbf(top: Clothing, bottom: Clothing) -> float:
    """Outfit_CBF(t,b) = เฉลี่ย preference ของ top และ bottom."""
    return round((top.preference_score + bottom.preference_score) / 2, 3)


def weighted_score(top: Clothing, bottom: Clothing) -> float:
    """S(t,b) = 0.6 * CBF + 0.4 * Color."""
    cbf = outfit_cbf(top, bottom)
    color = color_harmony_score(top, bottom)
    return round(CBF_WEIGHT * cbf + COLOR_WEIGHT * color, 3)


def _passes_rules(item: Clothing, matrix_a: MatrixA) -> bool:
    rules = matrix_a.forbidden_rules
    hex_c = item.dominant_color_hex.lower()
    r = int(hex_c[1:3], 16)
    g = int(hex_c[3:5], 16)
    b = int(hex_c[5:7], 16)

    if "no_black_solid" in rules and r < 40 and g < 40 and b < 40:
        return False
    if "no_shorts" in rules and item.category in ("shorts", "skirt"):
        return False
    if "no_sporty" in rules and item.category == "sportswear":
        return False
    if "no_revealing" in rules and item.category in ("tank", "crop"):
        return False
    return True


def recommend_top3(user_id: str, matrix_a: MatrixA) -> list[OutfitPair]:
    """
    Part 2 pipeline:
    1. Matrix B from closet
    2. Rule filter
    3. Pair tops + bottoms
    4. CBF + Color + Weighted Sum
    5. Top-3
    """
    items = list(Clothing.objects.filter(user_id=user_id))
    tops = [i for i in items if i.garment_type == GARMENT_TOP and _passes_rules(i, matrix_a)]
    bottoms = [i for i in items if i.garment_type == GARMENT_BOTTOM and _passes_rules(i, matrix_a)]

    if not tops or not bottoms:
        return []

    pairs: list[OutfitPair] = []
    for t in tops:
        for b in bottoms:
            if t.id == b.id:
                continue
            cbf = outfit_cbf(t, b)
            color = color_harmony_score(t, b)
            total = round(CBF_WEIGHT * cbf + COLOR_WEIGHT * color, 3)
            pairs.append(OutfitPair(
                top=t, bottom=b,
                cbf_score=cbf, color_score=color,
                total_score=total,
                total_percent=int(round(total * 100)),
            ))

    pairs.sort(key=lambda p: p.total_score, reverse=True)
    return pairs[:TOP_N]
