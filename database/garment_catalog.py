"""หมวดหมู่เสื้อผ้า — แบ่งกลุ่มสำหรับ UI และ map กลับประเภทหลักสำหรับ logic แนะนำชุด."""

from __future__ import annotations

# หมวดหมู่แบบแบ่งกลุ่ม (แสดงใน dropdown)
GARMENT_CATEGORY_GROUPS: list[tuple[str, list[tuple[str, str]]]] = [
    (
        "หมวดเสื้อ",
        [
            ("t_shirt", "เสื้อยืด"),
            ("polo", "เสื้อโปโล"),
            ("shirt", "เสื้อเชิ้ต"),
            ("tank_top", "เสื้อกล้าม / สายเดี่ยว"),
            ("crop_top", "เสื้อครอป"),
        ],
    ),
    (
        "หมวดกางเกง",
        [
            ("jeans", "กางเกงยีนส์"),
            ("slacks", "กางเกงสแล็ก"),
            ("chinos", "กางเกงชิโน่"),
            ("shorts", "กางเกงขาสั้น"),
            ("joggers", "กางเกงจ็อกเกอร์"),
            ("sweatpants", "กางเกงวอร์ม"),
            ("leggings", "กางเกงเลกกิ้ง"),
        ],
    ),
    (
        "หมวดกระโปรงและชุดชิ้นเดียว",
        [
            ("skirt", "กระโปรง"),
            ("dress", "ชุดเดรส"),
            ("jumpsuit", "ชุดจั๊มสูท"),
        ],
    ),
    (
        "หมวดเสื้อตัวนอก",
        [
            ("suit", "เสื้อสูท"),
            ("blazer", "เบลเซอร์"),
            ("jacket", "เสื้อแจ็กเก็ต"),
            ("hoodie", "เสื้อฮู้ด"),
            ("sweater", "สเวตเตอร์"),
            ("cardigan", "เสื้อคาร์ดิแกน"),
        ],
    ),
]

# รายการแบน (ใช้ใน model choices)
GARMENT_TYPES: list[tuple[str, str]] = [
    item for _group, items in GARMENT_CATEGORY_GROUPS for item in items
]

GARMENT_LABELS = dict(GARMENT_TYPES)

# ประเภทหลักสำหรับ Matrix A / destination rules (เดิม 7 ประเภท)
GARMENT_BASE_TYPE: dict[str, str] = {
    "t_shirt": "t_shirt",
    "polo": "shirt",
    "shirt": "shirt",
    "tank_top": "t_shirt",
    "crop_top": "t_shirt",
    "jeans": "pants",
    "slacks": "pants",
    "chinos": "pants",
    "shorts": "shorts",
    "joggers": "pants",
    "sweatpants": "pants",
    "leggings": "pants",
    "skirt": "skirt",
    "dress": "dress",
    "jumpsuit": "jumpsuit",
    "suit": "suit",
    "blazer": "jacket",
    "jacket": "jacket",
    "hoodie": "jacket",
    "sweater": "shirt",
    "cardigan": "jacket",
    # legacy
    "blouse": "blouse",
    "pants": "pants",
}

TOP_TYPES = {
    "t_shirt", "polo", "shirt", "tank_top", "crop_top",
    "suit", "blazer", "jacket", "hoodie", "sweater", "cardigan",
    "blouse", "dress", "jumpsuit",
}

BOTTOM_TYPES = {
    "jeans", "slacks", "chinos", "shorts", "joggers", "sweatpants", "leggings",
    "skirt", "pants",
}

# ชุดชิ้นเดียว / เซ็ตครบ — ไม่ต้องจับคู่ท่อนบน+ล่าง
FULL_OUTFIT_TYPES = {"dress", "jumpsuit", "suit"}
ONE_PIECE_TYPES = FULL_OUTFIT_TYPES

DEFAULT_FORMALITY: dict[str, int] = {
    "t_shirt": 2, "polo": 3, "shirt": 4, "tank_top": 1, "crop_top": 2,
    "jeans": 2, "slacks": 5, "chinos": 3, "shorts": 1, "joggers": 2,
    "sweatpants": 1, "leggings": 2,
    "skirt": 3, "dress": 4, "jumpsuit": 4,
    "suit": 6, "blazer": 5, "jacket": 5, "hoodie": 2, "sweater": 3, "cardigan": 4,
    "blouse": 4, "pants": 3,
}


def get_base_garment_type(garment_type: str) -> str:
    return GARMENT_BASE_TYPE.get(garment_type, garment_type)


def is_full_outfit(garment_type: str) -> bool:
    """เดรส / จั๊มสูท / สูท — นับเป็นชุดเซ็ต ไม่จับคู่กับท่อนล่าง."""
    return garment_type in FULL_OUTFIT_TYPES


LEGACY_GARMENT_ALIASES: dict[str, str] = {
    "pants": "jeans",
    "blouse": "shirt",
}


def normalize_garment_type(garment_type: str) -> str:
    """แปลงประเภทเก่า/ไม่รู้จักให้ตรงกับรายการใน dropdown."""
    if garment_type in GARMENT_LABELS:
        return garment_type
    return LEGACY_GARMENT_ALIASES.get(garment_type, garment_type)


def infer_part(garment_type: str) -> str:
    if garment_type in BOTTOM_TYPES:
        return "bottom"
    if garment_type in TOP_TYPES:
        return "top"
    return "top"


def grouped_choices(include_all: bool = False) -> list:
    """Choices สำหรับ Django form — รองรับ optgroup."""
    choices: list = []
    if include_all:
        choices.append(("", "ทั้งหมด"))
    for group_label, items in GARMENT_CATEGORY_GROUPS:
        choices.append((group_label, items))
    return choices
