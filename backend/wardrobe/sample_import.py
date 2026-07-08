"""Import mock wardrobe images from the user's sample folder into static + manifest."""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

from PIL import Image

from database.garment_catalog import DEFAULT_FORMALITY, normalize_garment_type

from wardrobe.forms import color_label_for_hex, snap_to_palette
from wardrobe.mock_data import _classify_garment, _extract_dominant_color
from wardrobe.services.destination_profiles import DEFAULT_FABRIC_THICKNESS

ROOT = Path(__file__).resolve().parents[2]
# ไฟล์ต้นฉบับอยู่ใน repo — ไม่พึ่ง path ภายนอก
DEFAULT_SOURCE = ROOT / "mock_samples" / "wardrobe" / "source"
CURATED_MANIFEST = ROOT / "mock_samples" / "wardrobe" / "default_manifest.json"
STATIC_DIR = ROOT / "frontend" / "static" / "mock" / "wardrobe"
MANIFEST_PATH = STATIC_DIR / "manifest.json"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".avif"}

# ลำดับสำคัญ — ตรวจเฉพาะเจาะจงก่อนประเภทกว้าง
_FILENAME_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("ขาสั้น", "shorts", "short", "beachshort"), "shorts"),
    (("เลกกิ้ง", "leggings", "legging"), "leggings"),
    (("จ็อก", "jogger", "joggers"), "joggers"),
    (("วอร์ม", "sweatpant", "sweatpants", "trackpant"), "sweatpants"),
    (("ยีนส์", "jeans", "denim"), "jeans"),
    (("สแล็ก", "slacks", "trouser"), "slacks"),
    (("ชิโน", "chino", "chinos"), "chinos"),
    (("กระโปรง", "skirt"), "skirt"),
    (("จั๊ม", "jumpsuit", "jump suit"), "jumpsuit"),
    (("เดรส", "dress"), "dress"),
    (("สูท", "suit"), "suit"),
    (("เบลเซอร์", "blazer"), "blazer"),
    (("ฮู้ด", "hoodie", "hoody"), "hoodie"),
    (("คาร์ดิ", "cardigan"), "cardigan"),
    (("สเวต", "sweater", "knit"), "sweater"),
    (("แจ็ค", "jacket"), "jacket"),
    (("โปโล", "polo"), "polo"),
    (("กล้าม", "tank", "camisole", "sleeveless"), "tank_top"),
    (("ครอป", "crop"), "crop_top"),
    (("บลาวส์", "blouse"), "blouse"),
    (("ยืด", "t-shirt", "tshirt", "tee"), "t_shirt"),
    (("เชิ้ต", "shirt"), "shirt"),
    (("กางเกง", "pants", "-bp_", "bp_"), "jeans"),
)


def _slug(name: str, max_len: int = 40) -> str:
    name = unicodedata.normalize("NFKC", Path(name).stem)
    name = re.sub(r"[^\w\u0E00-\u0E7F-]+", "-", name, flags=re.UNICODE)
    name = re.sub(r"-+", "-", name).strip("-").lower()
    return (name or "item")[:max_len]


def parse_garment_type(filename: str, width: int, height: int) -> str:
    lower = filename.lower()
    for keywords, garment_type in _FILENAME_RULES:
        if any(kw in lower for kw in keywords):
            return normalize_garment_type(garment_type)
    garment_type, _, _ = _classify_garment(width, height)
    aspect = width / height if height else 1.0
    if 0.92 <= aspect <= 1.08:
        return "shirt"
    return normalize_garment_type(garment_type)


def _copy_as_jpg(src: Path, dest: Path) -> None:
    img = Image.open(src)
    img.load()
    img = img.convert("RGB")
    img.thumbnail((800, 1000))
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, format="JPEG", quality=85)


def _write_curated_manifest() -> list[dict]:
    entries = json.loads(CURATED_MANIFEST.read_text(encoding="utf-8"))
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return prune_manifest_entries(save_curated=True)


def resolve_image_file(img_key: str) -> Path | None:
    """หาไฟล์รูปจริง — ใช้ร่วมกับ mock_data._image_file_for_key logic."""
    path = STATIC_DIR / f"{img_key}.jpg"
    if path.is_file() and path.stat().st_size >= 256:
        return path
    prefix = img_key.split("_", 1)[0]
    if prefix.isdigit():
        for candidate in sorted(STATIC_DIR.glob(f"{prefix}_*.jpg")):
            if candidate.stat().st_size >= 256:
                return candidate
    return None


def prune_manifest_entries(*, save_curated: bool = True) -> list[dict]:
    """เก็บเฉพาะรายการที่มีไฟล์รูปจริง แล้วเซฟ manifest."""
    if not MANIFEST_PATH.is_file():
        return []

    raw = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    kept: list[dict] = []
    for rec in raw:
        img = resolve_image_file(rec["img_key"])
        if not img:
            continue
        kept.append({**rec, "img_key": img.stem})

    if len(kept) < len(raw):
        for i, rec in enumerate(kept, start=1):
            rec["pk"] = i

    MANIFEST_PATH.write_text(
        json.dumps(kept, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if save_curated:
        CURATED_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        CURATED_MANIFEST.write_text(
            json.dumps(kept, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return kept


def build_manifest(source_dir: Path | str | None = None, *, curated: bool = True) -> list[dict]:
    if curated and CURATED_MANIFEST.is_file():
        return _write_curated_manifest()

    source_dir = Path(source_dir) if source_dir else DEFAULT_SOURCE
    if not source_dir.is_dir():
        raise FileNotFoundError(f"ไม่พบโฟลเดอร์ตัวอย่าง: {source_dir}")

    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    for old in STATIC_DIR.glob("*.jpg"):
        if old.name != ".gitkeep":
            old.unlink(missing_ok=True)

    entries: list[dict] = []
    files = sorted(
        p for p in source_dir.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    )

    for pk, src in enumerate(files, start=1):
        img = Image.open(src)
        img.load()
        w, h = img.size
        hex_code = snap_to_palette(_extract_dominant_color(img))
        garment_type = parse_garment_type(src.name, w, h)
        slug = _slug(src.name)
        img_key = f"{pk:02d}_{slug}"
        dest = STATIC_DIR / f"{img_key}.jpg"
        _copy_as_jpg(src, dest)

        entries.append({
            "pk": pk,
            "img_key": img_key,
            "source_name": src.name,
            "garment_type": garment_type,
            "color_hex": hex_code,
            "color_name_th": color_label_for_hex(hex_code),
            "formality": DEFAULT_FORMALITY.get(garment_type, 3),
            "fabric_thickness": DEFAULT_FABRIC_THICKNESS.get(garment_type, "medium"),
        })

    MANIFEST_PATH.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return entries
