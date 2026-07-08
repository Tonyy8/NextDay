"""Mock data layer for MOCK_MODE — drives a full-site mockup without real DB/AI writes.

All context builders here return dictionaries whose keys match exactly what the
shared templates expect (same keys as the real DB-backed views), so templates work
unchanged whether MOCK_MODE is on or off.
"""

from __future__ import annotations

import base64
from datetime import timedelta
from pathlib import Path

from django.utils import timezone

from database.garment_catalog import (
    BOTTOM_TYPES,
    DEFAULT_FORMALITY,
    GARMENT_CATEGORY_GROUPS,
    GARMENT_LABELS,
    GARMENT_TYPES,
    TOP_TYPES,
    get_base_garment_type,
    infer_part,
    is_full_outfit,
    normalize_garment_type,
)
from database.models import FABRIC_THICKNESS_CHOICES
from wardrobe.forms import (
    FORMALITY_CHOICES,
    WARDROBE_COLORS,
    WardrobeSearchForm,
    color_label_for_hex,
    snap_to_palette,
)
from wardrobe.services.color_utils import rgb_to_lab, thai_color_name
from wardrobe.services.destination_profiles import (
    DEFAULT_FABRIC_THICKNESS,
    DESTINATION_PROFILES,
    STYLE_LABELS,
    THICKNESS_LABELS,
    WEATHER_LABELS,
    build_matrix_a,
)
from wardrobe.services.outfit_engine import OutfitBuilder
from wardrobe.services.outfit_scorer import OutfitScoringEngine
from wardrobe.services.weather import fetch_weather

DEMO_USERNAME = "demo"
DEMO_EMAIL = "demo@nextday.app"

SESSION_EDIT_KEY = "mock_item_edits"
SESSION_UPLOAD_KEY = "mock_uploaded_items"
SESSION_PENDING_UPLOAD_KEY = "mock_pending_upload"
SESSION_DELETED_KEY = "mock_deleted_pks"
SESSION_FAVORITES_KEY = "mock_favorites"
SESSION_HIDDEN_FAVORITES_KEY = "mock_hidden_favorite_pks"
SESSION_COMMUNITY_KEY = "mock_community_posts"
SESSION_FEEDBACK_KEY = "mock_feedbacks"
UPLOAD_PK_BASE = 1000
MAX_UPLOAD_BATCH = 20
FAVORITE_PK_BASE = 2000
COMMUNITY_PK_BASE = 5000

FORMALITY_MAP = DEFAULT_FORMALITY
AI_CONFIDENCE_THRESHOLD = 0.6

# ── Garment metadata rules (part ↔ type ↔ color ต้องสอดคล้องกัน) ─────────────

_PALETTE_NAMES = dict(WARDROBE_COLORS)


def infer_part_from_garment(garment_type: str) -> str:
    """ท่อนบน/ล่าง อิงจากประเภทเสื้อผ้าเสมอ — ไม่ให้ part กับ type ขัดกัน."""
    return infer_part(garment_type)


def normalize_item_metadata(
    *,
    garment_type: str,
    part: str | None = None,
    formality: int | None = None,
    fabric_thickness: str | None = None,
    primary_color_hex: str,
    color_name_th: str | None = None,
) -> dict:
    """จัด part, ความเป็นทางการ, ความหนา, สี ให้ถูกต้องและ snap สีเข้า palette."""
    garment_type = normalize_garment_type(garment_type or "t_shirt")
    part = infer_part_from_garment(garment_type)

    if formality is None:
        formality = FORMALITY_MAP.get(garment_type, 3)
    if not fabric_thickness:
        fabric_thickness = DEFAULT_FABRIC_THICKNESS.get(garment_type, "medium")

    hex_code = snap_to_palette(primary_color_hex)
    palette_name = color_label_for_hex(hex_code)
    if color_name_th and color_name_th == _PALETTE_NAMES.get(hex_code):
        final_name = color_name_th
    else:
        final_name = palette_name

    return {
        "part": part,
        "garment_type": garment_type,
        "formality": int(formality),
        "fabric_thickness": fabric_thickness,
        "primary_color_hex": hex_code,
        "color_name_th": final_name,
    }


def _make_mock_item(
    pk,
    img_key,
    garment_type,
    color_hex,
    *,
    formality=None,
    fabric_thickness=None,
    color_name_th=None,
    garment_type_display=None,
    needs_review=False,
    is_verified=True,
    created_offset_hours=0,
):
    meta = normalize_item_metadata(
        garment_type=garment_type,
        formality=formality,
        fabric_thickness=fabric_thickness,
        primary_color_hex=color_hex,
        color_name_th=color_name_th,
    )
    image_url = _resolve_mock_image(img_key, color_hex)
    return MockClothingItem(
        pk,
        meta["part"],
        meta["garment_type"],
        meta["formality"],
        meta["fabric_thickness"],
        meta["primary_color_hex"],
        image_url=image_url,
        color_name_th=meta["color_name_th"],
        garment_type_display=garment_type_display,
        needs_review=needs_review,
        is_verified=is_verified,
        created_offset_hours=created_offset_hours,
    )

# Local mock photos (bundled under frontend/static — works offline, no broken CDN links)
_MOCK_IMG = "/static/mock/wardrobe"
_STATIC_MOCK_DIR = Path(__file__).resolve().parents[2] / "frontend" / "static" / "mock" / "wardrobe"
_MIN_IMAGE_BYTES = 256


def _image_file_for_key(img_key: str) -> Path | None:
    """หาไฟล์รูปจริงบนดิสก์ (รองรับชื่อไฟล์ไม่ตรง manifest)."""
    path = _STATIC_MOCK_DIR / f"{img_key}.jpg"
    if path.is_file() and path.stat().st_size >= _MIN_IMAGE_BYTES:
        return path
    prefix = img_key.split("_", 1)[0]
    if prefix.isdigit():
        for candidate in sorted(_STATIC_MOCK_DIR.glob(f"{prefix}_*.jpg")):
            if candidate.stat().st_size >= _MIN_IMAGE_BYTES:
                return candidate
    return None


def _mock_img(name: str) -> str:
    from django.templatetags.static import static

    return static(f"mock/wardrobe/{name}.jpg")


def _resolve_mock_image(img_key: str, color_hex: str) -> str:
    """ใช้รูป static ถ้ามี ไม่งั้น fallback เป็น swatch สี (ไม่ broken img)."""
    if img_key in IMG:
        return IMG[img_key]
    path = _image_file_for_key(img_key)
    if path:
        return _mock_img(path.stem)
    return _placeholder(color_hex)


IMG = {}


def _placeholder(hex_code: str) -> str:
    """Return a tiny inline SVG swatch as a data URI (works offline, no media files)."""
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="320" height="380">'
        f'<rect width="100%" height="100%" fill="{hex_code}"/>'
        '<rect x="0" y="0" width="100%" height="100%" fill="rgba(0,0,0,0.04)"/>'
        '</svg>' 
    )
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def _hex_to_rgb(hex_code: str) -> tuple[int, int, int]:
    h = hex_code.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


class MockFieldFile:
    """Mimics Django's FieldFile enough for templates: truthy + .url."""

    def __init__(self, url: str):
        self._url = url

    @property
    def url(self) -> str:
        return self._url

    def __bool__(self) -> bool:
        return bool(self._url)


class MockClothingItem:
    def __init__(
        self,
        pk,
        part,
        garment_type,
        formality,
        fabric_thickness,
        primary_color_hex,
        image_url=None,
        color_name_th=None,
        garment_type_display=None,
        needs_review=False,
        is_verified=True,
        created_offset_hours=0,
    ):
        norm = normalize_item_metadata(
            garment_type=garment_type,
            part=part,
            formality=formality,
            fabric_thickness=fabric_thickness,
            primary_color_hex=primary_color_hex,
            color_name_th=color_name_th,
        )
        self.pk = pk
        self.id = pk
        self.part = norm["part"]
        self.garment_type = norm["garment_type"]
        self.formality = norm["formality"]
        self.fabric_thickness = norm["fabric_thickness"]
        self.primary_color_hex = norm["primary_color_hex"]
        self.color_name_th = norm["color_name_th"]
        self.garment_type_display = garment_type_display
        self.needs_review = needs_review
        self.is_verified = is_verified
        self.confidence = 0.92
        r, g, b = _hex_to_rgb(primary_color_hex)
        self.lab_l, self.lab_a, self.lab_b = rgb_to_lab(r, g, b)
        self.dominant_colors = [primary_color_hex]
        self.image = MockFieldFile(image_url or _placeholder(primary_color_hex))
        self.cropped_image = self.image
        self.created_at = timezone.now() - timedelta(hours=created_offset_hours)

    def get_garment_type_display(self):
        if self.garment_type_display:
            return self.garment_type_display
        return GARMENT_LABELS.get(self.garment_type, self.garment_type)

    def get_fabric_thickness_display(self):
        return THICKNESS_LABELS.get(self.fabric_thickness, self.fabric_thickness)

    @property
    def display_name(self):
        return f"{self.get_garment_type_display()} สี{self.color_name_th}"


class MockDestination:
    def __init__(self, pk, name, slug, formality_level, allowed_categories, icon, description):
        self.pk = pk
        self.id = pk
        self.name = name
        self.slug = slug
        self.formality_level = formality_level
        self.allowed_categories = allowed_categories
        self.icon = icon
        self.description = description
        profile = DESTINATION_PROFILES.get(slug, {})
        self.weather = profile.get("weather", "mild")
        self.style = profile.get("style", "casual")
        self.garment_rules = profile.get("garment_rules", {})


class MockFavorite:
    def __init__(
        self,
        pk,
        destination,
        top_item,
        bottom_item=None,
        name="",
        match_score=0,
        match_theory="",
        full_outfit=False,
    ):
        self.pk = pk
        self.id = pk
        self.destination = destination
        self.top_item = top_item
        self.bottom_item = bottom_item
        self.name = name
        self.match_score = match_score
        self.match_theory = match_theory
        self.is_full_outfit = full_outfit or (
            bottom_item is None and is_full_outfit(top_item.garment_type)
        )


# ── Mock wardrobe ─────────────────────────────────────────────────────────────

DESTINATIONS = [
    MockDestination(1, "อยู่บ้าน", "home", 1, ["t_shirt", "shorts"], "🏠", "ชิลๆ สบายตัวที่บ้าน"),
    MockDestination(2, "เดินห้าง", "mall", 2, ["t_shirt", "shirt", "pants", "shorts"], "🛍️", "เดินเล่น ช้อปปิ้ง คาเฟ่"),
    MockDestination(3, "ออฟฟิศ", "office", 4, ["shirt", "blouse", "pants", "skirt"], "💼", "ทำงาน ประชุม สุภาพเรียบร้อย"),
    MockDestination(4, "ปาร์ตี้", "party", 5, ["shirt", "blouse", "dress", "jumpsuit", "jacket", "pants", "skirt"], "🎉", "งานเลี้ยง สังสรรค์ยามค่ำ"),
    MockDestination(5, "งานแต่ง", "wedding", 6, ["shirt", "blouse", "dress", "jumpsuit", "suit", "jacket", "pants", "skirt"], "💍", "งานพิธี — เดรส จั๊มสูท สูท (เลี่ยงชุดดำ/ขาวล้วน)"),
    MockDestination(6, "ออกกำลัง", "sport", 1, ["t_shirt", "shorts"], "🏃", "ฟิตเนส วิ่ง กิจกรรมกลางแจ้ง"),
]

# ครบ 7 ประเภทตาม dropdown (database.models.GARMENT_TYPES) — ชิ้นละ 1 ประเภท
# ใส่รูปจริงที่ frontend/static/mock/wardrobe/<img_key>.jpg
_MOCK_CATALOG = []


def _load_items_from_manifest():
    """โหลดเสื้อผ้าจาก manifest.json (สร้างจาก mock_samples/wardrobe/source)."""
    import json

    manifest_path = _STATIC_MOCK_DIR / "manifest.json"
    if not manifest_path.is_file():
        try:
            from wardrobe.sample_import import DEFAULT_SOURCE, build_manifest

            if DEFAULT_SOURCE.is_dir() and any(DEFAULT_SOURCE.iterdir()):
                build_manifest(DEFAULT_SOURCE)
        except Exception:
            return []

    if not manifest_path.is_file():
        return []

    items = []
    for rec in json.loads(manifest_path.read_text(encoding="utf-8")):
        img_file = _image_file_for_key(rec["img_key"])
        if not img_file:
            continue
        rec = {**rec, "img_key": img_file.stem}
        meta = normalize_item_metadata(
            garment_type=rec["garment_type"],
            formality=rec.get("formality"),
            fabric_thickness=rec.get("fabric_thickness"),
            primary_color_hex=rec["color_hex"],
            color_name_th=rec.get("color_name_th"),
        )
        items.append(
            MockClothingItem(
                rec["pk"],
                meta["part"],
                meta["garment_type"],
                meta["formality"],
                meta["fabric_thickness"],
                meta["primary_color_hex"],
                image_url=_resolve_mock_image(rec["img_key"], meta["primary_color_hex"]),
                color_name_th=meta["color_name_th"],
                created_offset_hours=rec["pk"] * 24,
            )
        )
    return items


_MANIFEST_MTIME: float | None = None
_ITEMS_CACHE: list = []


def _get_static_items() -> list:
    """โหลด manifest ใหม่เมื่อไฟล์เปลี่ยน (ไม่ต้อง restart server)."""
    global _MANIFEST_MTIME, _ITEMS_CACHE
    manifest_path = _STATIC_MOCK_DIR / "manifest.json"
    if not manifest_path.is_file():
        _ITEMS_CACHE = []
        _MANIFEST_MTIME = None
        return _ITEMS_CACHE
    mtime = manifest_path.stat().st_mtime
    if _MANIFEST_MTIME != mtime or not _ITEMS_CACHE:
        _ITEMS_CACHE = _load_items_from_manifest()
        _MANIFEST_MTIME = mtime
    return _ITEMS_CACHE


ITEMS = _get_static_items()


def _find(pk):
    for item in _get_static_items():
        if item.pk == pk:
            return item
    return None


_FAVORITE_NAMES = {
    "home": "ชุดชิลๆ อยู่บ้าน",
    "mall": "ชุดห้างสุดสบาย",
    "office": "ชุดออฟฟิศ",
    "party": "ชุดงานเลี้ยง",
    "wedding": "ชุดงานแต่ง",
    "sport": "ชุดออกกำลังกาย",
}


def _humanize_pair_theory(top, bottom, score: float) -> str:
    if score >= 70:
        quality = "เข้ากันดี"
    elif score >= 50:
        quality = "เข้ากันพอใช้"
    else:
        quality = "เข้ากันน้อย"
    return (
        f"จับคู่สี · {top.get_garment_type_display()} + {bottom.get_garment_type_display()} · "
        f"{quality} ({round(score)}%)"
    )


def _humanize_full_outfit_theory(top, destination=None) -> str:
    label = top.get_garment_type_display()
    color = top.color_name_th
    if destination:
        from wardrobe.services.outfit_scorer import build_matrix_a, build_matrix_b, score_correctness, score_weather

        matrix_a = build_matrix_a(destination)
        piece_b = build_matrix_b(top)
        corr = score_correctness(piece_b, matrix_a)
        weather = score_weather(piece_b, matrix_a.weather)
        return (
            f"ชุดเซ็ต · {label} สี{color} · "
            f"เหมาะสถานที่ {corr:.0f}% · อากาศ {weather:.0f}%"
        )
    return f"ชุดเซ็ต · {label} สี{color} · ไม่ต้องจับคู่ท่อนบน/ล่าง"


def _build_default_favorites():
    """ชุดโปรด — จับคู่ top/bottom หรือชุดเซ็ต (เดรส/จั๊มสูท/สูท) ที่ดีที่สุดต่อสถานที่."""
    from wardrobe.services.outfit_engine import ColorMatcher
    from wardrobe.services.outfit_scorer import (
        FULL_OUTFIT_COLOR_SCORE,
        WEIGHT_COLOR,
        WEIGHT_CORRECTNESS,
        WEIGHT_WEATHER,
        build_matrix_a,
        build_matrix_b,
        passes_hard_filter,
        score_correctness,
        score_weather,
    )

    items = _get_static_items()
    tops = [i for i in items if i.part == "top" and not is_full_outfit(i.garment_type)]
    bottoms = [i for i in items if i.part == "bottom"]
    full_items = [i for i in items if is_full_outfit(i.garment_type)]
    if not tops and not full_items:
        return []

    matcher = ColorMatcher()
    favorites = []
    used_items: set[int] = set()
    for fav_pk, dest in enumerate(DESTINATIONS, start=1):
        matrix_a = build_matrix_a(dest)
        ranked: list[tuple[float, str, object, object | None, bool]] = []

        for top in tops:
            top_b = build_matrix_b(top)
            if not passes_hard_filter(top_b, matrix_a):
                continue
            for bottom in bottoms:
                bottom_b = build_matrix_b(bottom)
                if not passes_hard_filter(bottom_b, matrix_a):
                    continue
                match = matcher.score_pair(top, bottom)
                ranked.append((
                    match.score,
                    _humanize_pair_theory(top, bottom, match.score),
                    top,
                    bottom,
                    False,
                ))

        for piece in full_items:
            piece_b = build_matrix_b(piece)
            if not passes_hard_filter(piece_b, matrix_a):
                continue
            corr = score_correctness(piece_b, matrix_a)
            weather = score_weather(piece_b, matrix_a.weather)
            score = (
                WEIGHT_CORRECTNESS * corr
                + WEIGHT_WEATHER * weather
                + WEIGHT_COLOR * FULL_OUTFIT_COLOR_SCORE
            )
            theory = _humanize_full_outfit_theory(piece, dest)
            ranked.append((score, theory, piece, None, True))

        ranked.sort(key=lambda row: row[0], reverse=True)
        chosen = None
        for score, theory, top, bottom, as_full in ranked:
            if top.pk in used_items:
                continue
            if not as_full and bottom and (top.pk, bottom.pk) in {
                (f.top_item.pk, f.bottom_item.pk)
                for f in favorites
                if not f.is_full_outfit and f.bottom_item
            }:
                continue
            chosen = (score, theory, top, bottom, as_full)
            break
        if not chosen:
            continue
        score, theory, top, bottom, as_full = chosen
        used_items.add(top.pk)
        favorites.append(
            MockFavorite(
                fav_pk,
                dest,
                top,
                bottom,
                _FAVORITE_NAMES.get(dest.slug, f"ชุด{dest.name}"),
                round(score),
                theory,
                full_outfit=as_full,
            )
        )
    return favorites


_FAVORITES_MTIME: float | None = None
_FAVORITES_CACHE: list = []


def _get_default_favorites() -> list:
    global _FAVORITES_MTIME, _FAVORITES_CACHE
    manifest_path = _STATIC_MOCK_DIR / "manifest.json"
    mtime = manifest_path.stat().st_mtime if manifest_path.is_file() else None
    if _FAVORITES_MTIME != mtime or not _FAVORITES_CACHE:
        _FAVORITES_CACHE = _build_default_favorites()
        _FAVORITES_MTIME = mtime
    return _FAVORITES_CACHE


# โพสต์คอมมูนิตี้ — รูปชุดแฟชั่นเดิม (bundled ที่ static/mock/community)
_COMMUNITY_STATIC = Path(__file__).resolve().parents[2] / "frontend" / "static" / "mock" / "community"

COMMUNITY_POSTS = [
    {
        "pk": 1,
        "author": "mint",
        "initial": "M",
        "caption": "ชุดออกกำลังกาย",
        "time_ago": "2 ชม.",
        "image_key": "01_mint",
    },
    {
        "pk": 2,
        "author": "nara",
        "initial": "N",
        "caption": "ลุคไฮโซ",
        "time_ago": "5 ชม.",
        "image_key": "02_nara",
    },
    {
        "pk": 3,
        "author": "beam",
        "initial": "B",
        "caption": "ชุดไปทำงาน",
        "time_ago": "เมื่อวาน",
        "image_key": "03_beam",
    },
    {
        "pk": 4,
        "author": "ploy",
        "initial": "P",
        "caption": "ชุดไปทะเลชิวๆ",
        "time_ago": "เมื่อวาน",
        "image_key": "04_ploy",
    },
    {
        "pk": 5,
        "author": "tong",
        "initial": "T",
        "caption": "เดรสสีพาสเทลไปเดท",
        "time_ago": "2 วัน",
        "image_key": "05_tong",
    },
    {
        "pk": 6,
        "author": "fah",
        "initial": "F",
        "caption": "สตรีทแวร์วันหยุด",
        "time_ago": "3 วัน",
        "image_key": "06_fah",
    },
]


# ── Image analysis for uploads (Pillow-only, no heavy AI deps) ────────────────

def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return "#{:02x}{:02x}{:02x}".format(int(r), int(g), int(b))


def _extract_dominant_color(image) -> str:
    """Find the main garment colour from a real photo, skipping plain white/black
    backgrounds when a more saturated colour is available."""
    img = image.convert("RGB")
    img.thumbnail((80, 80))
    quant = img.quantize(colors=8)
    palette = quant.getpalette()
    counts = sorted(quant.getcolors() or [], reverse=True)
    fallback = None
    for _count, idx in counts:
        r, g, b = palette[idx * 3], palette[idx * 3 + 1], palette[idx * 3 + 2]
        if fallback is None:
            fallback = (r, g, b)
        mx, mn = max(r, g, b), min(r, g, b)
        if mx > 244 and mn > 238:  # near-white background
            continue
        if mx < 26:  # near-black background
            continue
        return _rgb_to_hex(r, g, b)
    if fallback:
        return _rgb_to_hex(*fallback)
    return "#9ca3af"


def _image_to_data_uri(image) -> str:
    """Downscale + JPEG-encode as a base64 data URI so no media files are needed."""
    import io

    img = image.convert("RGB")
    img.thumbnail((400, 500))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def _classify_garment(width: int, height: int) -> tuple[str, str, float]:
    """จำแนกประเภท + ท่อนจากสัดส่วนรูป (สอดคล้อง ClothingProcessor)."""
    aspect = width / height if height else 1.0
    if aspect >= 1.25:
        return "jeans", "bottom", 0.82
    if aspect >= 1.05:
        return "shorts", "bottom", 0.74
    if aspect >= 0.95:
        return "skirt", "bottom", 0.70
    if aspect <= 0.72:
        return "t_shirt", "top", 0.84
    if aspect <= 0.85:
        return "shirt", "top", 0.72
    return "shirt", "top", 0.76


def _mock_item_from_upload_rec(rec: dict) -> MockClothingItem:
    meta = normalize_item_metadata(
        garment_type=rec["garment_type"],
        part=rec.get("part"),
        formality=rec.get("formality"),
        fabric_thickness=rec.get("fabric_thickness"),
        primary_color_hex=rec["primary_color_hex"],
        color_name_th=rec.get("color_name_th"),
    )
    return MockClothingItem(
        pk=rec["pk"],
        part=meta["part"],
        garment_type=meta["garment_type"],
        formality=meta["formality"],
        fabric_thickness=meta["fabric_thickness"],
        primary_color_hex=meta["primary_color_hex"],
        image_url=rec["image"],
        color_name_th=meta["color_name_th"],
        needs_review=rec.get("needs_review", False),
        is_verified=not rec.get("needs_review", False),
    )


def analyze_upload_batch(request, files):
    """วิเคราะห์รูปที่อัปโหลด — เก็บชั่วคราวรอผู้ใช้กดบันทึก (ยังไม่เข้าตู้)."""
    from PIL import Image

    uploads = request.session.get(SESSION_UPLOAD_KEY, [])
    next_pk = UPLOAD_PK_BASE + len(uploads)
    pending = []
    for f in files:
        try:
            image = Image.open(f)
            try:
                image.draft("RGB", (600, 750))
            except Exception:
                pass
            image.load()
        except Exception:
            continue
        w, h = image.size
        hex_code = _extract_dominant_color(image)
        garment_type, part, confidence = _classify_garment(w, h)
        meta = normalize_item_metadata(
            garment_type=garment_type,
            part=part,
            primary_color_hex=hex_code,
        )
        needs_review = confidence < AI_CONFIDENCE_THRESHOLD
        record = {
            "pk": next_pk,
            **meta,
            "image": _image_to_data_uri(image),
            "needs_review": needs_review,
            "confidence": round(confidence, 2),
        }
        pending.append(record)
        next_pk += 1

    request.session[SESSION_PENDING_UPLOAD_KEY] = pending
    request.session.modified = True
    return pending


def get_pending_uploads(request):
    pending = request.session.get(SESSION_PENDING_UPLOAD_KEY, [])
    return [_mock_item_from_upload_rec(rec) for rec in pending if _upload_has_image(rec)]


def confirm_pending_uploads(request, selected_pks: list[int]) -> int:
    pending = request.session.get(SESSION_PENDING_UPLOAD_KEY, [])
    if not pending:
        return 0
    selected = {int(p) for p in selected_pks}
    to_save = [rec for rec in pending if rec["pk"] in selected and _upload_has_image(rec)]
    uploads = request.session.get(SESSION_UPLOAD_KEY, [])
    uploads.extend(to_save)
    request.session[SESSION_UPLOAD_KEY] = uploads
    request.session.pop(SESSION_PENDING_UPLOAD_KEY, None)
    request.session.modified = True
    return len(to_save)


def discard_pending_uploads(request) -> None:
    request.session.pop(SESSION_PENDING_UPLOAD_KEY, None)
    request.session.modified = True


def add_uploaded_items(request, files):
    """Legacy alias — วิเคราะห์แล้วเก็บรอบันทึก."""
    return analyze_upload_batch(request, files)


# ── Session-based item edits ──────────────────────────────────────────────────

def _all_base_items(request):
    """Static demo items (minus deleted) plus session uploads."""
    _clean_session_uploads(request)
    deleted = set(request.session.get(SESSION_DELETED_KEY, []))
    items = [item for item in _get_static_items() if item.pk not in deleted]
    for rec in request.session.get(SESSION_UPLOAD_KEY, []):
        meta = normalize_item_metadata(
            garment_type=rec["garment_type"],
            part=rec.get("part"),
            formality=rec.get("formality"),
            fabric_thickness=rec.get("fabric_thickness"),
            primary_color_hex=rec["primary_color_hex"],
            color_name_th=rec.get("color_name_th"),
        )
        items.append(
            MockClothingItem(
                pk=rec["pk"],
                part=meta["part"],
                garment_type=meta["garment_type"],
                formality=meta["formality"],
                fabric_thickness=meta["fabric_thickness"],
                primary_color_hex=meta["primary_color_hex"],
                image_url=rec["image"],
                color_name_th=meta["color_name_th"],
                needs_review=rec.get("needs_review", False),
                is_verified=not rec.get("needs_review", False),
            )
        )
    return items


def _upload_has_image(rec: dict) -> bool:
    img = (rec.get("image") or "").strip()
    return img.startswith("data:image/") and len(img) > 200


def _clean_session_uploads(request) -> None:
    uploads = request.session.get(SESSION_UPLOAD_KEY, [])
    clean = [u for u in uploads if _upload_has_image(u)]
    if len(clean) != len(uploads):
        request.session[SESSION_UPLOAD_KEY] = clean
        request.session.modified = True


def reset_mock_wardrobe_session(request) -> None:
    """คืนเสื้อผ้าเริ่มต้นทั้งหมด — ล้างรายการที่ลบและอัปโหลดเสียใน session."""
    request.session.pop(SESSION_DELETED_KEY, None)
    request.session.pop(SESSION_UPLOAD_KEY, None)
    request.session.pop(SESSION_PENDING_UPLOAD_KEY, None)
    request.session.modified = True


def delete_item(request, pk):
    """Remove an item from the mock wardrobe (session-backed)."""
    pk = int(pk)
    if pk >= UPLOAD_PK_BASE:
        uploads = request.session.get(SESSION_UPLOAD_KEY, [])
        request.session[SESSION_UPLOAD_KEY] = [u for u in uploads if u["pk"] != pk]
    else:
        deleted = set(request.session.get(SESSION_DELETED_KEY, []))
        deleted.add(pk)
        request.session[SESSION_DELETED_KEY] = list(deleted)
    edits = request.session.get(SESSION_EDIT_KEY, {})
    edits.pop(str(pk), None)
    request.session[SESSION_EDIT_KEY] = edits
    request.session.modified = True


def _items_with_edits(request):
    edits = request.session.get(SESSION_EDIT_KEY, {})
    base_items = _all_base_items(request)
    if not edits:
        return base_items
    result = []
    for base in base_items:
        data = edits.get(str(base.pk))
        if not data:
            result.append(base)
            continue
        meta = normalize_item_metadata(
            garment_type=data.get("garment_type", base.garment_type),
            part=data.get("part", base.part),
            formality=int(data.get("formality", base.formality)),
            fabric_thickness=data.get("fabric_thickness", base.fabric_thickness),
            primary_color_hex=data.get("primary_color_hex", base.primary_color_hex),
            color_name_th=data.get("color_name_th", base.color_name_th),
        )
        result.append(
            MockClothingItem(
                pk=base.pk,
                part=meta["part"],
                garment_type=meta["garment_type"],
                formality=meta["formality"],
                fabric_thickness=meta["fabric_thickness"],
                primary_color_hex=meta["primary_color_hex"],
                image_url=base.image.url,
                color_name_th=meta["color_name_th"],
                garment_type_display=data.get("garment_type_display", base.garment_type_display),
                needs_review=False,
                is_verified=True,
            )
        )
    return result


def get_item(pk, request):
    pk = int(pk)
    for item in _items_with_edits(request):
        if item.pk == pk:
            return item
    return None


def get_items_by_pks(request, pks):
    wanted = {int(p) for p in pks}
    return [item for item in _items_with_edits(request) if item.pk in wanted]


def get_destination(pk):
    pk = int(pk)
    for dest in DESTINATIONS:
        if dest.pk == pk:
            return dest
    return None


def save_item_edit(request, pk, cleaned_data):
    pk = int(pk)
    current = get_item(pk, request)
    base = current or _find(pk)
    hex_code = cleaned_data["primary_color_hex"]
    if base and snap_to_palette(hex_code) == snap_to_palette(base.primary_color_hex):
        color_name_th = base.color_name_th
    else:
        color_name_th = color_label_for_hex(hex_code)

    garment_type_display = None
    if base and cleaned_data["garment_type"] == base.garment_type:
        garment_type_display = base.garment_type_display

    meta = normalize_item_metadata(
        garment_type=cleaned_data["garment_type"],
        part=cleaned_data["part"],
        formality=int(cleaned_data["formality"]),
        fabric_thickness=cleaned_data["fabric_thickness"],
        primary_color_hex=hex_code,
        color_name_th=color_name_th,
    )

    edits = request.session.get(SESSION_EDIT_KEY, {})
    edits[str(pk)] = {
        **meta,
        "garment_type_display": garment_type_display,
    }
    request.session[SESSION_EDIT_KEY] = edits
    request.session.modified = True
    return get_item(pk, request)


# ── Outfit URL helpers (mirror the real view helpers) ─────────────────────────

def _parse_slot_overrides(request, count=3):
    overrides = {}
    for i in range(count):
        top = request.GET.get(f"t{i}")
        bottom = request.GET.get(f"b{i}")
        if top or bottom:
            overrides[i] = {}
            if top:
                overrides[i]["top"] = int(top)
            if bottom:
                overrides[i]["bottom"] = int(bottom)
    return overrides


def _build_outfit_query(destination, slot_idx, piece, item_pk, overrides):
    params = [f"destination={destination.pk}"]
    slots = {i: dict(overrides.get(i, {})) for i in range(3)}
    if piece == "top":
        slots[slot_idx]["top"] = item_pk
    else:
        slots[slot_idx]["bottom"] = item_pk
    for i in range(3):
        if "top" in slots[i]:
            params.append(f"t{i}={slots[i]['top']}")
        if "bottom" in slots[i]:
            params.append(f"b{i}={slots[i]['bottom']}")
    return "?" + "&".join(params)


def _outfit_base_query(destination, outfits, overrides):
    params = [f"destination={destination.pk}"]
    for i, outfit in enumerate(outfits):
        top_pk = overrides.get(i, {}).get("top", outfit.top.pk)
        params.append(f"t{i}={top_pk}")
        if not outfit.is_full_outfit:
            bottom_pk = overrides.get(i, {}).get("bottom", outfit.bottom.pk)
            params.append(f"b{i}={bottom_pk}")
    return "&".join(params)


def _enrich_outfit_urls(destination, outfits, overrides):
    for i, outfit in enumerate(outfits):
        base = _outfit_base_query(destination, outfits, overrides)
        outfit.swap_top_url = f"?{base}&swap={i}&piece=top"
        if outfit.is_full_outfit:
            outfit.swap_bottom_url = ""
        else:
            outfit.swap_bottom_url = f"?{base}&swap={i}&piece=bottom"
    return f"?{_outfit_base_query(destination, outfits, overrides)}"


def _matrix_labels(destination):
    matrix_a = build_matrix_a(destination)
    return {
        "matrix_weather": WEATHER_LABELS.get(matrix_a.weather, matrix_a.weather),
        "matrix_style": STYLE_LABELS.get(matrix_a.style, matrix_a.style),
    }


# ── Context builders ──────────────────────────────────────────────────────────

def _meta(request):
    profile = get_profile(request)
    username = profile["display_name"]
    return username, (username[:1] or "U").upper()


def _build_favorite(request, pk, top_pk, bottom_pk, dest_pk, name, match_score, match_theory, full_outfit=False):
    top = get_item(top_pk, request)
    bottom = get_item(bottom_pk, request) if bottom_pk else None
    destination = get_destination(dest_pk) if dest_pk else None
    if not top:
        return None
    as_full = full_outfit or is_full_outfit(top.garment_type)
    if as_full:
        bottom = None
        display_theory = _humanize_full_outfit_theory(top, destination)
    else:
        if not bottom:
            return None
        display_theory = _humanize_pair_theory(top, bottom, match_score)
    return MockFavorite(
        pk, destination, top, bottom, name, match_score, display_theory,
        full_outfit=as_full,
    )


def get_favorites(request):
    hidden = set(request.session.get(SESSION_HIDDEN_FAVORITES_KEY, []))
    favorites = [f for f in _get_default_favorites() if f.pk not in hidden]
    for rec in request.session.get(SESSION_FAVORITES_KEY, []):
        fav = _build_favorite(
            request,
            rec["pk"],
            rec["top_pk"],
            rec.get("bottom_pk"),
            rec.get("dest_pk"),
            rec.get("name", ""),
            rec["match_score"],
            rec["match_theory"],
            full_outfit=rec.get("is_full_outfit", False),
        )
        if fav:
            favorites.insert(0, fav)
    return favorites


def save_favorite(request, top_pk, bottom_pk, dest_pk, name):
    from wardrobe.services.outfit_engine import ColorMatcher
    from wardrobe.services.outfit_scorer import (
        FULL_OUTFIT_COLOR_SCORE,
        WEIGHT_COLOR,
        WEIGHT_CORRECTNESS,
        WEIGHT_WEATHER,
        build_matrix_a,
        build_matrix_b,
        score_correctness,
        score_weather,
    )

    top = get_item(int(top_pk), request)
    if not top:
        return None

    if is_full_outfit(top.garment_type):
        destination = get_destination(dest_pk) if dest_pk else None
        matrix_a = build_matrix_a(destination) if destination else build_matrix_a(DESTINATIONS[0])
        piece_b = build_matrix_b(top)
        corr = score_correctness(piece_b, matrix_a)
        weather = score_weather(piece_b, matrix_a.weather)
        match_score = round(
            WEIGHT_CORRECTNESS * corr
            + WEIGHT_WEATHER * weather
            + WEIGHT_COLOR * FULL_OUTFIT_COLOR_SCORE
        )
        match_theory = _humanize_full_outfit_theory(top, destination)
        bottom_pk_val = None
        is_full = True
    else:
        bottom = get_item(int(bottom_pk), request)
        if not bottom:
            return None
        match = ColorMatcher().score_pair(top, bottom)
        match_score = round(match.score)
        match_theory = _humanize_pair_theory(top, bottom, match.score)
        bottom_pk_val = int(bottom_pk)
        is_full = False

    session_favs = request.session.get(SESSION_FAVORITES_KEY, [])
    pk = FAVORITE_PK_BASE + len(session_favs)
    record = {
        "pk": pk,
        "top_pk": int(top_pk),
        "bottom_pk": bottom_pk_val,
        "dest_pk": int(dest_pk) if dest_pk else None,
        "name": name or "",
        "match_score": match_score,
        "match_theory": match_theory,
        "is_full_outfit": is_full,
    }
    session_favs.append(record)
    request.session[SESSION_FAVORITES_KEY] = session_favs
    request.session.modified = True
    return _build_favorite(
        request, pk, record["top_pk"], record["bottom_pk"],
        record["dest_pk"], record["name"], record["match_score"], record["match_theory"],
        full_outfit=is_full,
    )


def delete_favorite(request, pk):
    pk = int(pk)
    if pk < FAVORITE_PK_BASE:
        hidden = set(request.session.get(SESSION_HIDDEN_FAVORITES_KEY, []))
        hidden.add(pk)
        request.session[SESSION_HIDDEN_FAVORITES_KEY] = list(hidden)
    else:
        session_favs = request.session.get(SESSION_FAVORITES_KEY, [])
        request.session[SESSION_FAVORITES_KEY] = [f for f in session_favs if f["pk"] != pk]
    request.session.modified = True


def _community_image(image_key: str) -> str:
    from django.templatetags.static import static

    community_path = _COMMUNITY_STATIC / f"{image_key}.jpg"
    if community_path.is_file():
        return static(f"mock/community/{image_key}.jpg")
    path = _image_file_for_key(image_key)
    if path:
        return static(f"mock/wardrobe/{path.stem}.jpg")
    return _placeholder("#9ca3af")


def _all_community_posts(request):
    profile = get_profile(request)
    username = profile["display_name"]
    user_posts = []
    for rec in request.session.get(SESSION_COMMUNITY_KEY, []):
        user_posts.append({**rec, "is_mine": rec.get("author") == username})
    static_posts = []
    for rec in COMMUNITY_POSTS:
        post = {**rec, "is_mine": False}
        post["image"] = _community_image(rec["image_key"])
        static_posts.append(post)
    return user_posts + static_posts


def add_community_post(request, image_file, caption):
    from PIL import Image

    image = Image.open(image_file)
    try:
        image.draft("RGB", (600, 750))
    except Exception:
        pass
    image.load()
    profile = get_profile(request)
    author = profile["display_name"]
    posts = request.session.get(SESSION_COMMUNITY_KEY, [])
    pk = COMMUNITY_PK_BASE + len(posts)
    posts.insert(0, {
        "pk": pk,
        "author": author,
        "initial": (author[:1] or "U").upper(),
        "caption": caption or "ลุคใหม่",
        "time_ago": "เมื่อกี้",
        "image": _image_to_data_uri(image),
        "is_mine": True,
    })
    request.session[SESSION_COMMUNITY_KEY] = posts
    request.session.modified = True
    return pk


def delete_community_post(request, post_id):
    post_id = int(post_id)
    posts = request.session.get(SESSION_COMMUNITY_KEY, [])
    request.session[SESSION_COMMUNITY_KEY] = [p for p in posts if p["pk"] != post_id]
    request.session.modified = True


def save_feedback(request, kind, subject, detail):
    feedbacks = request.session.get(SESSION_FEEDBACK_KEY, [])
    entry = {
        "pk": len(feedbacks) + 1,
        "kind": kind,
        "subject": subject,
        "detail": detail,
        "created": timezone.now().strftime("%d/%m/%Y %H:%M"),
        "status": "รับเรื่องแล้ว",
    }
    feedbacks.insert(0, entry)
    request.session[SESSION_FEEDBACK_KEY] = feedbacks[:20]
    request.session.modified = True
    return entry


def feedback_context(request):
    return {"recent_feedbacks": request.session.get(SESSION_FEEDBACK_KEY, [])}


def dashboard_context(request):
    items = _items_with_edits(request)
    color_map = {}
    for item in items:
        color_map.setdefault(item.primary_color_hex, item.color_name_th or item.primary_color_hex)
    unique_colors = [{"hex": h, "name": n} for h, n in list(color_map.items())[:8]]

    dest_stats = []
    for dest in DESTINATIONS:
        allowed = set(dest.allowed_categories)
        count = sum(1 for i in items if get_base_garment_type(i.garment_type) in allowed)
        dest_stats.append({"dest": dest, "count": count})

    avg_formality = sum(i.formality for i in items) / len(items) if items else 0
    favorites = get_favorites(request)
    latest_fav = favorites[0] if favorites else None
    username, avatar_letter = _meta(request)

    return {
        "total": len(items),
        "needs_review": sum(1 for i in items if i.needs_review),
        "favorites_count": len(favorites),
        "suggest_today": min(3, len(favorites)),
        "recent": items[:3],
        "destinations": dest_stats,
        "unique_colors": unique_colors,
        "latest_fav": latest_fav,
        "match_score": round(latest_fav.match_score) if latest_fav else 0,
        "diversity": min(100, len(color_map) * 12),
        "formality_pct": round(avg_formality / 6 * 100) if items else 0,
        "unused_count": sum(1 for i in items if not i.is_verified),
        "username": username,
        "avatar_letter": avatar_letter,
        "weather": fetch_weather(),
    }


def wardrobe_context(request):
    if _get_static_items() and not _all_base_items(request):
        reset_mock_wardrobe_session(request)

    form = WardrobeSearchForm(request.GET or None)
    all_items = _items_with_edits(request)
    items = list(all_items)
    if form.is_valid():
        q = form.cleaned_data.get("q")
        gt = form.cleaned_data.get("garment_type")
        if q:
            ql = q.lower()
            items = [
                i for i in items
                if ql in i.color_name_th.lower()
                or ql in i.garment_type.lower()
                or ql in i.get_garment_type_display().lower()
            ]
        if gt:
            items = [i for i in items if i.garment_type == gt]
    return {
        "items": items,
        "total_items": len(all_items),
        "form": form,
        "garment_category_groups": GARMENT_CATEGORY_GROUPS,
        "color_choices": WARDROBE_COLORS,
        "formality_choices": FORMALITY_CHOICES,
        "thickness_choices": FABRIC_THICKNESS_CHOICES,
    }


def _edit_context(pk, request):
    item = get_item(pk, request)
    return {
        "item": item,
        "edit_initial": {
            "garment_type": item.garment_type,
            "part": item.part,
            "formality": item.formality,
            "fabric_thickness": item.fabric_thickness,
            "primary_color_hex": snap_to_palette(item.primary_color_hex),
        },
    }


def item_edit_context(pk, request):
    return _edit_context(pk, request)


def verify_context(pk, request):
    return _edit_context(pk, request)


def outfit_context(request):
    dest_id = request.GET.get("destination")
    swap_slot = request.GET.get("swap")
    swap_piece = request.GET.get("piece")
    ctx = {
        "destinations": DESTINATIONS,
        "step": 1,
        "swap_slot": swap_slot,
        "swap_piece": swap_piece,
    }
    if not dest_id:
        return ctx

    destination = get_destination(dest_id) or DESTINATIONS[0]
    user_items = _items_with_edits(request)
    overrides = _parse_slot_overrides(request)
    outfits = OutfitScoringEngine().suggest_outfits(user_items, destination, slot_overrides=overrides)
    outfit_base_url = _enrich_outfit_urls(destination, outfits, overrides)

    ctx.update({
        "step": 2,
        "destination": destination,
        "outfits": outfits,
        "slot_overrides": overrides,
        "outfit_base_url": outfit_base_url,
        **_matrix_labels(destination),
    })

    if swap_slot not in (None, "") and swap_piece in ("top", "bottom"):
        slot_idx = int(swap_slot)
        if slot_idx < len(outfits):
            current = outfits[slot_idx]
            if current.is_full_outfit:
                ref_item = current.top
            elif swap_piece == "top":
                ref_item = current.top
            else:
                ref_item = current.bottom
            alts = OutfitBuilder().part_alternatives(ref_item, user_items, destination)
            ctx["swap_mode"] = True
            ctx["swap_alternatives"] = [
                {
                    "item": alt,
                    "url": _build_outfit_query(destination, slot_idx, swap_piece, alt.pk, overrides),
                }
                for alt in alts[:6]
            ]
            ctx["swap_current"] = ref_item
            ctx["swap_is_full_outfit"] = current.is_full_outfit

    return ctx


def favorites_context(request):
    return {"outfits": get_favorites(request)}


def community_context(request):
    username, avatar_letter = _meta(request)
    return {
        "posts": _all_community_posts(request),
        "username": username,
        "avatar_letter": avatar_letter,
    }


def manual_outfit_context(request):
    items = _items_with_edits(request)
    return {
        "tops": [i for i in items if i.part == "top"],
        "bottoms": [i for i in items if i.part == "bottom"],
        "destinations": DESTINATIONS,
    }


SESSION_PROFILE_KEY = "mock_profile"

DEFAULT_PROFILE = {
    "display_name": DEMO_USERNAME,
    "email": DEMO_EMAIL,
    "style_pref": "สมาร์ทแคชชวล",
    "weight_correctness": 40,
    "weight_weather": 20,
    "weight_color": 40,
}


def get_profile(request):
    profile = dict(DEFAULT_PROFILE)
    profile.update(request.session.get(SESSION_PROFILE_KEY, {}))
    return profile


def save_profile(request, cleaned_data):
    profile = dict(DEFAULT_PROFILE)
    profile.update(request.session.get(SESSION_PROFILE_KEY, {}))
    profile.update({
        "display_name": cleaned_data["display_name"],
        "email": cleaned_data["email"],
        "style_pref": cleaned_data["style_pref"],
        "weight_correctness": int(cleaned_data["weight_correctness"]),
        "weight_weather": int(cleaned_data["weight_weather"]),
        "weight_color": int(cleaned_data["weight_color"]),
    })
    request.session[SESSION_PROFILE_KEY] = profile
    request.session.modified = True


def profile_context(request):
    items = _items_with_edits(request)
    profile = get_profile(request)
    favorites = get_favorites(request)
    return {
        "username": profile["display_name"],
        "email": profile["email"],
        "total_items": len(items),
        "favorites_count": len(favorites),
        "style_pref": profile["style_pref"],
        "weight_correctness": profile["weight_correctness"],
        "weight_weather": profile["weight_weather"],
        "weight_color": profile["weight_color"],
        "profile_initial": {
            "display_name": profile["display_name"],
            "email": profile["email"],
            "style_pref": profile["style_pref"],
            "weight_correctness": profile["weight_correctness"],
            "weight_weather": profile["weight_weather"],
            "weight_color": profile["weight_color"],
        },
    }
