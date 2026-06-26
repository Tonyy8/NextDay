"""Matrix A lookup table — เกณฑ์ชุดที่ถูกต้องตามสถานที่ (ความเป็นทางการ × ประเภท, อากาศ, สไตล์)."""

from __future__ import annotations

from dataclasses import dataclass, field

WEATHER_LABELS = {
    "hot": "ร้อน",
    "mild": "อุ่นสบาย",
    "cool": "เย็น/แอร์",
}

STYLE_LABELS = {
    "casual": "สบายๆ",
    "smart_casual": "สมาร์ทแคชชวล",
    "formal": "ทางการ",
    "sporty": "กีฬา",
}

# คะแนนความหนาผ้า vs สภาพอากาศ (0-100)
WEATHER_THICKNESS_SCORE = {
    "hot": {"thin": 100, "medium": 55, "thick": 15},
    "mild": {"thin": 75, "medium": 100, "thick": 65},
    "cool": {"thin": 35, "medium": 80, "thick": 100},
}

DEFAULT_FABRIC_THICKNESS = {
    "t_shirt": "thin",
    "shirt": "thin",
    "blouse": "thin",
    "jacket": "medium",
    "pants": "medium",
    "shorts": "thin",
    "skirt": "thin",
}

THICKNESS_LABELS = {
    "thin": "บาง",
    "medium": "ปานกลาง",
    "thick": "หนา",
}


def _rules(formality_min, formality_max, thickness):
    return {
        "formality_min": formality_min,
        "formality_max": formality_max,
        "thickness_allowed": thickness,
    }


DESTINATION_PROFILES = {
    "home": {
        "weather": "hot",
        "style": "casual",
        "garment_rules": {
            "t_shirt": _rules(1, 2, ["thin"]),
            "shorts": _rules(1, 2, ["thin"]),
        },
    },
    "mall": {
        "weather": "mild",
        "style": "casual",
        "garment_rules": {
            "t_shirt": _rules(1, 3, ["thin", "medium"]),
            "shirt": _rules(2, 3, ["thin", "medium"]),
            "pants": _rules(2, 3, ["medium"]),
            "shorts": _rules(1, 2, ["thin"]),
        },
    },
    "office": {
        "weather": "cool",
        "style": "smart_casual",
        # ออฟฟิศ: เน้นสุภาพ เลี่ยงสีฉูดฉาด
        "avoid_colors": {"ส้ม", "เหลือง", "ชมพู"},
        "garment_rules": {
            "shirt": _rules(3, 5, ["thin", "medium"]),
            "blouse": _rules(3, 5, ["thin", "medium"]),
            "pants": _rules(3, 5, ["medium", "thick"]),
            "skirt": _rules(3, 5, ["thin", "medium"]),
        },
    },
    "party": {
        "weather": "cool",
        "style": "formal",
        "garment_rules": {
            "shirt": _rules(4, 6, ["thin", "medium"]),
            "blouse": _rules(4, 6, ["thin", "medium"]),
            "jacket": _rules(4, 6, ["medium", "thick"]),
            "pants": _rules(4, 6, ["medium", "thick"]),
            "skirt": _rules(4, 6, ["thin", "medium"]),
        },
    },
    "wedding": {
        "weather": "cool",
        "style": "formal",
        # มารยาทไทย: เลี่ยงชุดดำล้วน (งานศพ) และขาวล้วน (สีเจ้าสาว)
        "avoid_colors": {"ดำ", "ขาว"},
        "garment_rules": {
            "shirt": _rules(5, 6, ["thin", "medium"]),
            "blouse": _rules(5, 6, ["thin", "medium"]),
            "jacket": _rules(5, 6, ["medium", "thick"]),
            "pants": _rules(5, 6, ["medium", "thick"]),
            "skirt": _rules(5, 6, ["thin", "medium"]),
        },
    },
    "sport": {
        "weather": "hot",
        "style": "sporty",
        "garment_rules": {
            "t_shirt": _rules(1, 2, ["thin"]),
            "shorts": _rules(1, 2, ["thin"]),
        },
    },
}


@dataclass
class MatrixA:
    name: str
    slug: str
    formality_level: int
    weather: str
    style: str
    allowed_categories: set[str]
    garment_rules: dict[str, dict] = field(default_factory=dict)
    avoid_colors: set[str] = field(default_factory=set)


def build_matrix_a(destination) -> MatrixA:
    """สร้าง Matrix A จาก Destination model หรือ mock object."""
    slug = getattr(destination, "slug", "")
    profile = DESTINATION_PROFILES.get(slug, {})
    rules = getattr(destination, "garment_rules", None) or profile.get("garment_rules", {})
    avoid = getattr(destination, "avoid_colors", None) or profile.get("avoid_colors", set())
    return MatrixA(
        name=destination.name,
        slug=slug,
        formality_level=destination.formality_level,
        weather=getattr(destination, "weather", None) or profile.get("weather", "mild"),
        style=getattr(destination, "style", None) or profile.get("style", "casual"),
        allowed_categories=set(destination.allowed_categories),
        garment_rules=rules,
        avoid_colors=set(avoid),
    )
