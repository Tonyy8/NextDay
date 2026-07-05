"""Mock data layer for MOCK_MODE — drives a full-site mockup without real DB/AI writes.

All context builders here return dictionaries whose keys match exactly what the
shared templates expect (same keys as the real DB-backed views), so templates work
unchanged whether MOCK_MODE is on or off.
"""

from __future__ import annotations

import base64
from datetime import timedelta

from django.utils import timezone

from database.models import FABRIC_THICKNESS_CHOICES, GARMENT_TYPES
from wardrobe.forms import FORMALITY_CHOICES, WARDROBE_COLORS, WardrobeSearchForm, snap_to_palette
from wardrobe.services.color_utils import rgb_to_lab, thai_color_name
from wardrobe.services.destination_profiles import (
    DESTINATION_PROFILES,
    STYLE_LABELS,
    THICKNESS_LABELS,
    WEATHER_LABELS,
    build_matrix_a,
)
from wardrobe.services.outfit_engine import OutfitBuilder
from wardrobe.services.outfit_scorer import OutfitScoringEngine

DEMO_USERNAME = "demo"
DEMO_EMAIL = "demo@nextday.app"

GARMENT_LABELS = dict(GARMENT_TYPES)
SESSION_EDIT_KEY = "mock_item_edits"
SESSION_UPLOAD_KEY = "mock_uploaded_items"
UPLOAD_PK_BASE = 1000

# Real fashion photos for the mockup (Unsplash)
IMG = {
    "top_white": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=400&h=500&fit=crop",    
    "top_blue": "https://images.unsplash.com/photo-1583743814966-8936f5b7be1a?w=400&h=500&fit=crop",
    "top_blouse": "https://images.unsplash.com/photo-1594633312681-425c7b97ccd1?w=400&h=500&fit=crop",
    "top_blouse_pink": "https://images.unsplash.com/photo-1581044777550-4cfa60707c03?w=400&h=500&fit=crop",
    "top_jacket": "https://images.unsplash.com/photo-1551028719-00167b16eac5?w=400&h=500&fit=crop",
    "top_stripe": "https://images.unsplash.com/photo-1576566588028-4147f3842f27?w=400&h=500&fit=crop",
    "top_tshirt_cream": "https://images.unsplash.com/photo-1503341504253-dff4815485f1?w=400&h=500&fit=crop",
    "top_polo": "https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?w=400&h=500&fit=crop",
    "top_shirt_light_blue": "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=500&fit=crop",
    "pants_navy": "https://images.unsplash.com/photo-1473966968600-fa801b869a1a?w=400&h=500&fit=crop",
    "pants_blue": "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=400&h=500&fit=crop",
    "pants_beige": "https://images.unsplash.com/photo-1594938298603-c8148c4dae35?w=400&h=500&fit=crop",
    "shorts": "https://images.unsplash.com/photo-1591195853828-11db59a44f6b?w=400&h=500&fit=crop",
    "skirt": "https://images.unsplash.com/photo-1583496661160-fb5886a0aaaa?w=400&h=500&fit=crop",
    "pants_black": "https://images.unsplash.com/photo-1542272604-787c3835535d?w=400&h=500&fit=crop",
    "pants_cream": "https://images.unsplash.com/photo-1506629082955-511b1aa562c8?w=400&h=500&fit=crop",
}


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
        self.pk = pk
        self.id = pk
        self.part = part
        self.garment_type = garment_type
        self.formality = formality
        self.fabric_thickness = fabric_thickness
        self.primary_color_hex = primary_color_hex
        self.color_name_th = color_name_th or thai_color_name(primary_color_hex)
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
    def __init__(self, pk, destination, top_item, bottom_item, name, match_score, match_theory):
        self.pk = pk
        self.id = pk
        self.destination = destination
        self.top_item = top_item
        self.bottom_item = bottom_item
        self.name = name
        self.match_score = match_score
        self.match_theory = match_theory


# ── Mock wardrobe ─────────────────────────────────────────────────────────────

DESTINATIONS = [
    MockDestination(1, "อยู่บ้าน", "home", 1, ["t_shirt", "shorts"], "🏠", "ชิลๆ สบายตัวที่บ้าน"),
    MockDestination(2, "เดินห้าง", "mall", 2, ["t_shirt", "shirt", "pants", "shorts"], "🛍️", "เดินเล่น ช้อปปิ้ง คาเฟ่"),
    MockDestination(3, "ออฟฟิศ", "office", 4, ["shirt", "blouse", "pants", "skirt"], "💼", "ทำงาน ประชุม สุภาพเรียบร้อย"),
    MockDestination(4, "ปาร์ตี้", "party", 5, ["shirt", "blouse", "jacket", "pants", "skirt"], "🎉", "งานเลี้ยง สังสรรค์ยามค่ำ"),
    MockDestination(5, "งานแต่ง", "wedding", 6, ["shirt", "blouse", "jacket", "pants", "skirt"], "💍", "งานพิธี ทางการสุด"),
    MockDestination(6, "ออกกำลัง", "sport", 1, ["t_shirt", "shorts"], "🏃", "ฟิตเนส วิ่ง กิจกรรมกลางแจ้ง"),
]

ITEMS = [
    # Tops
    MockClothingItem(1, "top", "t_shirt", 4, "thin", "#f5f5f5", image_url=IMG["top_white"], color_name_th="ขาว", created_offset_hours=24),
    MockClothingItem(2, "top", "t_shirt", 2, "thin", "#2c5ead", image_url=IMG["top_blue"], color_name_th="ดำ", created_offset_hours=48),
    MockClothingItem(3, "top", "t_shirt", 4, "thin", "#fbcfe8", image_url=IMG["top_blouse_pink"], color_name_th="สีชมพูอ่อน", needs_review=True, is_verified=False, created_offset_hours=72),
    MockClothingItem(4, "top", "t_shirt", 2, "thin", "#f5f5f5", image_url=IMG["top_stripe"], color_name_th="ขาวลายน้ำเงิน", created_offset_hours=168),
    MockClothingItem(6, "top", "shirt", 3, "thin", "#93c5fd", image_url=IMG["top_shirt_light_blue"], color_name_th="ฟ้าอ่อน", created_offset_hours=240),
    # Bottoms
    MockClothingItem(7, "bottom", "pants", 4, "medium", "#d2b48c", image_url=IMG["pants_navy"], color_name_th="สีน้ำตาลอ่อน", created_offset_hours=24),
    MockClothingItem(8, "bottom", "pants", 3, "medium", "#2c5ead", image_url=IMG["pants_blue"], color_name_th="สีน้ำเงิน", created_offset_hours=96),
    MockClothingItem(9, "bottom", "shorts", 1, "thin", "#38bdf8", image_url=IMG["shorts"], color_name_th="สีฟ้า", created_offset_hours=144),
    MockClothingItem(10, "bottom", "skirt", 4, "thin", "#111827", image_url=IMG["skirt"], color_name_th="ดำ", created_offset_hours=192),
    MockClothingItem(11, "bottom", "pants", 5, "thick", "#111827", image_url=IMG["pants_black"], color_name_th="ดำ", garment_type_display="กางเกงยีน", created_offset_hours=288),
    MockClothingItem(12, "bottom", "pants", 3, "medium", "#86efac", image_url=IMG["pants_cream"], color_name_th="สีเขียวอ่อน", created_offset_hours=336),
]

def _find(pk):
    for item in ITEMS:
        if item.pk == pk:
            return item
    return None


FAVORITES = [
    MockFavorite(1, DESTINATIONS[2], _find(1), _find(7), "ชุดออฟฟิศ", 87, "Analogous · เข้ากันดี"),
    MockFavorite(2, DESTINATIONS[1], _find(2), _find(9), "ชุดห้างสุดสบาย", 79, "Complementary · คอนทราสต์พอดี"),
    MockFavorite(3, DESTINATIONS[3], _find(4), _find(11), "ชุดงานเลี้ยง", 91, "Monochromatic · โทนเดียวหรู"),
]

COMMUNITY_POSTS = [
    {"author": "mint", "initial": "M", "caption": "ชุดออกกำลังกาย", "time_ago": "2 ชม.", "image": "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=600&h=750&fit=crop"},
    {"author": "nara", "initial": "N", "caption": "ลุคไฮโซ", "time_ago": "5 ชม.", "image": "https://images.unsplash.com/photo-1483985988355-763728e1935b?w=600&h=750&fit=crop"},
    {"author": "beam", "initial": "B", "caption": "ชุดไปทำงาน", "time_ago": "เมื่อวาน", "image": "https://plusprinting.bookplus.co.th/wp-content/uploads/2023/01/simple-office-outfit-ideas-07.jpg"},
    {"author": "ploy", "initial": "P", "caption": "ชุดไปทะเลชิวๆ", "time_ago": "เมื่อวาน", "image": "https://images.unsplash.com/photo-1469334031218-e382a71b716b?w=600&h=750&fit=crop"},
    {"author": "tong", "initial": "T", "caption": "เดรสสีพาสเทลไปเดท", "time_ago": "2 วัน", "image": "https://images.unsplash.com/photo-1539008835657-9e8e9680c956?w=600&h=750&fit=crop"},
    {"author": "fah", "initial": "F", "caption": "สตรีทแวร์วันหยุด", "time_ago": "3 วัน", "image": "https://images.unsplash.com/photo-1529139574466-a303027c1d8b?w=600&h=750&fit=crop"},
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


def add_uploaded_items(request, files):
    """Analyse each uploaded photo (dominant colour + Thai colour name) and store
    it in the session so it appears across the mock wardrobe. Garment type defaults
    to a top and is flagged for review so the user can correct it."""
    from PIL import Image

    uploads = request.session.get(SESSION_UPLOAD_KEY, [])
    next_pk = UPLOAD_PK_BASE + len(uploads)
    created = []
    for f in files:
        try:
            image = Image.open(f)
            # Fast path for large phone JPEGs: decode at reduced size (much quicker)
            try:
                image.draft("RGB", (600, 750))
            except Exception:
                pass
            image.load()
        except Exception:
            continue
        hex_code = _extract_dominant_color(image)
        record = {
            "pk": next_pk,
            "part": "top",
            "garment_type": "t_shirt",
            "formality": 3,
            "fabric_thickness": "medium",
            "primary_color_hex": hex_code,
            "color_name_th": thai_color_name(hex_code),
            "image": _image_to_data_uri(image),
            "needs_review": True,
        }
        uploads.append(record)
        created.append(record)
        next_pk += 1

    request.session[SESSION_UPLOAD_KEY] = uploads
    request.session.modified = True
    return created


# ── Session-based item edits ──────────────────────────────────────────────────

def _all_base_items(request):
    """Static demo items plus any photos the user uploaded this session."""
    items = list(ITEMS)
    for rec in request.session.get(SESSION_UPLOAD_KEY, []):
        items.append(
            MockClothingItem(
                pk=rec["pk"],
                part=rec["part"],
                garment_type=rec["garment_type"],
                formality=rec["formality"],
                fabric_thickness=rec["fabric_thickness"],
                primary_color_hex=rec["primary_color_hex"],
                image_url=rec["image"],
                color_name_th=rec.get("color_name_th"),
                needs_review=rec.get("needs_review", False),
                is_verified=not rec.get("needs_review", False),
            )
        )
    return items


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
        result.append(
            MockClothingItem(
                pk=base.pk,
                part=data.get("part", base.part),
                garment_type=data.get("garment_type", base.garment_type),
                formality=int(data.get("formality", base.formality)),
                fabric_thickness=data.get("fabric_thickness", base.fabric_thickness),
                primary_color_hex=data.get("primary_color_hex", base.primary_color_hex),
                image_url=base.image.url,
                color_name_th=data.get("color_name_th", base.color_name_th),
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
    from wardrobe.forms import color_label_for_hex, snap_to_palette

    base = _find(int(pk))
    hex_code = cleaned_data["primary_color_hex"]
    if base and hex_code == snap_to_palette(base.primary_color_hex):
        color_name_th = base.color_name_th
    else:
        color_name_th = color_label_for_hex(hex_code)

    garment_type_display = None
    if base and cleaned_data["garment_type"] == base.garment_type:
        garment_type_display = base.garment_type_display

    edits = request.session.get(SESSION_EDIT_KEY, {})
    edits[str(pk)] = {
        "garment_type": cleaned_data["garment_type"],
        "part": cleaned_data["part"],
        "formality": int(cleaned_data["formality"]),
        "fabric_thickness": cleaned_data["fabric_thickness"],
        "primary_color_hex": hex_code,
        "color_name_th": color_name_th,
        "garment_type_display": garment_type_display,
    }
    request.session[SESSION_EDIT_KEY] = edits
    request.session.modified = True


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
        bottom_pk = overrides.get(i, {}).get("bottom", outfit.bottom.pk)
        params.append(f"t{i}={top_pk}")
        params.append(f"b{i}={bottom_pk}")
    return "&".join(params)


def _enrich_outfit_urls(destination, outfits, overrides):
    for i, outfit in enumerate(outfits):
        base = _outfit_base_query(destination, outfits, overrides)
        outfit.swap_top_url = f"?{base}&swap={i}&piece=top"
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
    username = DEMO_USERNAME
    return username, (username[:1] or "U").upper()


def dashboard_context(request):
    items = _items_with_edits(request)
    color_map = {}
    for item in items:
        color_map.setdefault(item.primary_color_hex, item.color_name_th or item.primary_color_hex)
    unique_colors = [{"hex": h, "name": n} for h, n in list(color_map.items())[:8]]

    dest_stats = []
    for dest in DESTINATIONS:
        allowed = set(dest.allowed_categories)
        count = sum(1 for i in items if i.garment_type in allowed)
        dest_stats.append({"dest": dest, "count": count})

    avg_formality = sum(i.formality for i in items) / len(items) if items else 0
    latest_fav = FAVORITES[0] if FAVORITES else None
    username, avatar_letter = _meta(request)

    return {
        "total": len(items),
        "needs_review": sum(1 for i in items if i.needs_review),
        "favorites_count": len(FAVORITES),
        "suggest_today": min(3, len(FAVORITES)),
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
    }


def wardrobe_context(request):
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
        "garment_types": GARMENT_TYPES,
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

    if swap_slot is not None and swap_piece in ("top", "bottom"):
        slot_idx = int(swap_slot)
        if slot_idx < len(outfits):
            current = outfits[slot_idx]
            ref_item = current.top if swap_piece == "top" else current.bottom
            alts = OutfitBuilder().part_alternatives(ref_item, user_items, destination)
            ctx["swap_alternatives"] = [
                {
                    "item": alt,
                    "url": _build_outfit_query(destination, slot_idx, swap_piece, alt.pk, overrides),
                }
                for alt in alts[:6]
            ]
            ctx["swap_current"] = ref_item

    return ctx


def favorites_context():
    return {"outfits": FAVORITES}


def community_context():
    return {
        "posts": COMMUNITY_POSTS,
        "username": DEMO_USERNAME,
        "avatar_letter": DEMO_USERNAME[:1].upper(),
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
    return {
        "username": profile["display_name"],
        "email": profile["email"],
        "total_items": len(items),
        "favorites_count": len(FAVORITES),
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
