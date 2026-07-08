import random
from dataclasses import dataclass

from database.garment_catalog import get_base_garment_type, is_full_outfit
from database.models import AISettings, BOTTOM_TYPES, ClothingItem, Destination, TOP_TYPES

from .color_utils import itten_relation, lab_distance, munsell_balance, rgb_to_hue


@dataclass
class MatchResult:
    item: ClothingItem
    score: float
    theory: str
    detail: str


@dataclass
class OutfitSuggestion:
    top: ClothingItem
    bottom: ClothingItem | None = None
    score: float = 0.0
    theory: str = ""
    detail: str = ""
    rank: int = 0
    correctness_score: float = 0.0
    weather_score: float = 0.0
    color_score: float = 0.0
    is_full_outfit: bool = False


class ColorMatcher:
    def __init__(self):
        self.settings = AISettings.get()

    def score_pair(self, top: ClothingItem, bottom: ClothingItem) -> MatchResult:
        delta = lab_distance(top.lab_l, top.lab_a, top.lab_b, bottom.lab_l, bottom.lab_a, bottom.lab_b)
        r1, g1, b1 = self._hex_rgb(top.primary_color_hex)
        r2, g2, b2 = self._hex_rgb(bottom.primary_color_hex)
        hue1, hue2 = rgb_to_hue(r1, g1, b1), rgb_to_hue(r2, g2, b2)

        goldilocks = self.settings.lab_min_delta <= delta <= self.settings.lab_max_delta
        itten = itten_relation(hue1, hue2)
        munsell = munsell_balance(top.lab_l, bottom.lab_l)

        score = 50.0
        if goldilocks:
            score += 30
        elif delta < self.settings.lab_min_delta:
            score += 10
        else:
            score += max(0, 20 - (delta - self.settings.lab_max_delta) * 0.3)

        if "Complementary" in itten or "Analogous" in itten or "Triadic" in itten:
            score += 15
        if "สมดุล" in munsell or "พอดี" in munsell:
            score += 5

        score = min(100, max(0, score))
        theory = f"Goldilocks ΔE={delta:.1f} | {itten} | {munsell}"
        detail = "เข้ากันดี" if score >= 70 else "เข้ากันพอใช้" if score >= 50 else "เข้ากันน้อย"

        return MatchResult(item=bottom, score=score, theory=theory, detail=detail)

    @staticmethod
    def _hex_rgb(hex_code: str):
        h = hex_code.lstrip("#")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

    def find_matching_bottoms(self, top: ClothingItem, candidates: list[ClothingItem], limit: int = 3) -> list[MatchResult]:
        results = [self.score_pair(top, b) for b in candidates]
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]


class WardrobeFilter:
    @staticmethod
    def filter_for_destination(items, destination: Destination):
        allowed = set(destination.allowed_categories)
        return [
            i for i in items
            if get_base_garment_type(i.garment_type) in allowed
            and i.formality <= destination.formality_level + 1
        ]

    @staticmethod
    def tops(items):
        return [i for i in items if i.part == "top" or i.garment_type in TOP_TYPES]

    @staticmethod
    def separates_tops(items):
        return [i for i in WardrobeFilter.tops(items) if not is_full_outfit(i.garment_type)]

    @staticmethod
    def full_outfits(items):
        return [i for i in items if is_full_outfit(i.garment_type)]

    @staticmethod
    def bottoms(items):
        return [i for i in items if i.part == "bottom" or i.garment_type in BOTTOM_TYPES]


class OutfitBuilder:
    def __init__(self):
        self.matcher = ColorMatcher()
        self.filter = WardrobeFilter()

    def suggest_tops(self, user_items, destination: Destination, count: int = 3) -> list[ClothingItem]:
        eligible = self.filter.filter_for_destination(user_items, destination)
        tops = self.filter.tops(eligible)
        if len(tops) <= count:
            return tops
        return random.sample(tops, count)

    def suggest_bottoms(self, top: ClothingItem, user_items, destination: Destination, count: int = 3) -> list[MatchResult]:
        eligible = self.filter.filter_for_destination(user_items, destination)
        bottoms = self.filter.bottoms(eligible)
        return self.matcher.find_matching_bottoms(top, bottoms, count)

    def color_alternatives(self, item: ClothingItem, user_items) -> list[ClothingItem]:
        """Type Lock: same garment_type only, different colors."""
        return [
            i for i in user_items
            if i.garment_type == item.garment_type and i.pk != item.pk
        ]

    def part_alternatives(self, item: ClothingItem, user_items, destination: Destination) -> list[ClothingItem]:
        eligible = self.filter.filter_for_destination(user_items, destination)
        if is_full_outfit(item.garment_type):
            pool = self.filter.full_outfits(eligible)
        elif item.part == "top" or item.garment_type in TOP_TYPES:
            pool = self.filter.separates_tops(eligible)
        else:
            pool = self.filter.bottoms(eligible)
        return [i for i in pool if i.pk != item.pk]

    def suggest_outfits(
        self,
        user_items,
        destination: Destination,
        count: int = 3,
        slot_overrides: dict | None = None,
    ) -> list[OutfitSuggestion]:
        from .outfit_scorer import OutfitScoringEngine

        return OutfitScoringEngine().suggest_outfits(
            user_items, destination, count=count, slot_overrides=slot_overrides
        )
