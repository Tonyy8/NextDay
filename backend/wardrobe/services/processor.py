import os
import uuid

import cv2
from django.conf import settings
from django.core.files.base import ContentFile

from database.models import AISettings, BOTTOM_TYPES, ClothingItem, TOP_TYPES

from .color_utils import rgb_to_lab, thai_color_name
from .destination_profiles import DEFAULT_FABRIC_THICKNESS

FORMALITY_MAP = {
    "shirt": 4, "blouse": 4, "jacket": 5,
    "t_shirt": 2, "pants": 3, "shorts": 1, "skirt": 3,
}


class ClothingProcessor:
    def __init__(self):
        from detection.services import ColorExtractor, YOLODetector  # lazy: heavy AI deps

        self.detector = YOLODetector()
        self.color_extractor = ColorExtractor()
        self.ai_settings = AISettings.get()

    def process_upload(self, user, uploaded_file) -> ClothingItem:
        temp_name = f"temp_{uuid.uuid4().hex}_{uploaded_file.name}"
        temp_path = os.path.join(settings.MEDIA_ROOT, "uploads", temp_name)
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)

        with open(temp_path, "wb") as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)

        detections = self.detector.detect(temp_path)
        det = detections[0] if detections else None

        bbox = det.bbox if det else None
        colors = self.color_extractor.extract_dominant_colors(temp_path, k=3, bbox=bbox)
        primary = colors[0] if colors else None

        confidence = det.confidence if det else 0.3
        aspect = det.aspect_ratio if det else 1.0
        garment_type, part = self._classify(aspect, confidence)

        hex_code = primary.hex_code if primary else "#808080"
        lab = rgb_to_lab(*primary.rgb) if primary else (50.0, 0.0, 0.0)

        item = ClothingItem(
            user=user,
            part=part,
            garment_type=garment_type,
            formality=FORMALITY_MAP.get(garment_type, 3),
            fabric_thickness=DEFAULT_FABRIC_THICKNESS.get(garment_type, "medium"),
            confidence=confidence,
            needs_review=confidence < self.ai_settings.confidence_threshold,
            is_verified=confidence >= self.ai_settings.confidence_threshold,
            primary_color_hex=hex_code,
            color_name_th=thai_color_name(hex_code),
            dominant_colors=[{"hex": c.hex_code, "percentage": c.percentage} for c in colors],
            lab_l=lab[0], lab_a=lab[1], lab_b=lab[2],
            bbox_x1=det.bbox[0] if det else 0,
            bbox_y1=det.bbox[1] if det else 0,
            bbox_x2=det.bbox[2] if det else 0,
            bbox_y2=det.bbox[3] if det else 0,
            aspect_ratio=aspect,
        )

        with open(temp_path, "rb") as img_file:
            item.image.save(uploaded_file.name, ContentFile(img_file.read()), save=False)

        if bbox and det:
            crop_path = temp_path.replace("temp_", "crop_")
            img = cv2.imread(temp_path)
            x1, y1, x2, y2 = bbox
            crop = img[y1:y2, x1:x2]
            if crop.size > 0:
                cv2.imwrite(crop_path, crop)
                with open(crop_path, "rb") as cf:
                    item.cropped_image.save(f"crop_{uuid.uuid4().hex}.jpg", ContentFile(cf.read()), save=False)
                os.remove(crop_path)

        item.save()
        os.remove(temp_path)
        return item

    @staticmethod
    def _classify(aspect_ratio: float, confidence: float) -> tuple[str, str]:
        if aspect_ratio >= 1.1:
            return "pants", "bottom"
        if aspect_ratio <= 0.75:
            return "t_shirt", "top"
        if confidence > 0.5:
            return "shirt", "top"
        return "t_shirt", "top"
