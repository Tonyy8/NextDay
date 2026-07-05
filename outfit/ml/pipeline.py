"""
Part 1 — อัปโหลดรูป:
  YOLOv8 → crop → OpenCV K-Means ดึงสีหลัก → ระบุ Top/Bottom
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# COCO class hints (person=0); ใช้ crop แล้วเดา top/bottom จากสัดส่วน
GARMENT_TOP = "top"
GARMENT_BOTTOM = "bottom"


@dataclass
class ScanResult:
    garment_type: str
    dominant_color_hex: str
    dominant_color_rgb: list[int]
    color_name: str
    yolo_used: bool
    category: str


class YOLOCropper:
    def __init__(self):
        self.model = None
        self._loaded = False

    def _load(self):
        if self._loaded:
            return
        try:
            from ultralytics import YOLO
            self.model = YOLO("yolov8n.pt")
            self._loaded = True
        except Exception as e:
            logger.warning("YOLO unavailable: %s", e)
            self._loaded = True

    def crop(self, img: Image.Image) -> tuple[Image.Image, bool]:
        self._load()
        if self.model is None:
            return self._center_crop(img), False
        try:
            results = self.model(img, verbose=False)[0]
            best_box, best_conf = None, 0.0
            for box in results.boxes:
                if int(box.cls[0]) == 0 and float(box.conf[0]) > best_conf:
                    best_conf = float(box.conf[0])
                    best_box = box.xyxy[0].tolist()
            if best_box and best_conf > 0.3:
                x1, y1, x2, y2 = [int(v) for v in best_box]
                w, h = img.size
                pad_x = int((x2 - x1) * 0.05)
                pad_y = int((y2 - y1) * 0.05)
                cropped = img.crop((
                    max(0, x1 - pad_x), max(0, y1 - pad_y),
                    min(w, x2 + pad_x), min(h, y2 + pad_y),
                ))
                return cropped, True
        except Exception as e:
            logger.warning("YOLO error: %s", e)
        return self._center_crop(img), False

    def _center_crop(self, img: Image.Image) -> Image.Image:
        w, h = img.size
        side = min(w, h)
        left = (w - side) // 2
        top = (h - side) // 2
        return img.crop((left, top, left + side, top + side))


def _guess_garment_type(img: Image.Image) -> str:
    """เดา Top/Bottom จากสัดส่วนภาพที่ crop แล้ว."""
    w, h = img.size
    ratio = h / max(w, 1)
    return GARMENT_TOP if ratio >= 1.05 else GARMENT_BOTTOM


def _extract_dominant_color(img: Image.Image) -> tuple[str, list[int], str]:
    """OpenCV K-Means ดึงเฉดสีหลัก."""
    arr = np.array(img.convert("RGB"))
    pixels = arr.reshape(-1, 3).astype(np.float32)
    if len(pixels) < 10:
        return "#808080", [128, 128, 128], "เทา"

    try:
        import cv2
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
        _, labels, centers = cv2.kmeans(
            pixels, 3, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS
        )
        counts = np.bincount(labels.flatten(), minlength=3)
        dominant = centers[int(np.argmax(counts))].astype(int)
    except ImportError:
        # fallback: mean color
        dominant = pixels.mean(axis=0).astype(int)

    r, g, b = [int(max(0, min(255, c))) for c in dominant]
    hex_color = f"#{r:02x}{g:02x}{b:02x}"
    name = _color_name(r, g, b)
    return hex_color, [r, g, b], name


def _color_name(r: int, g: int, b: int) -> str:
    if r > 200 and g > 200 and b > 200:
        return "ขาว"
    if r < 60 and g < 60 and b < 60:
        return "ดำ"
    if abs(r - g) < 30 and abs(g - b) < 30:
        return "เทา"
    if b > r and b > g:
        return "น้ำเงิน"
    if r > g and r > b:
        return "แดง/ชมพู"
    if g > r and g > b:
        return "เขียว"
    if r > 180 and g > 140:
        return "ครีม/เบจ"
    return "อื่นๆ"


def scan_clothing(image_bytes: bytes) -> ScanResult:
    """รัน pipeline ตามเอกสาร Part 1."""
    pil = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    cropper = YOLOCropper()
    cropped, yolo_used = cropper.crop(pil)
    garment_type = _guess_garment_type(cropped)
    hex_c, rgb, cname = _extract_dominant_color(cropped)
    category = "shirt" if garment_type == GARMENT_TOP else "pants"
    return ScanResult(
        garment_type=garment_type,
        dominant_color_hex=hex_c,
        dominant_color_rgb=rgb,
        color_name=cname,
        yolo_used=yolo_used,
        category=category,
    )
