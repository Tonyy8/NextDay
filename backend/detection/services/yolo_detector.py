import logging
from dataclasses import dataclass

import cv2
from django.conf import settings
from ultralytics import YOLO

logger = logging.getLogger(__name__)

CLOTHING_CLASSES = {
    "person",
    "tie",
    "suitcase",
    "handbag",
    "backpack",
    "umbrella",
}


@dataclass
class DetectionResult:
    class_name: str
    confidence: float
    bbox: tuple[int, int, int, int]
    aspect_ratio: float
    shape_label: str


class YOLODetector:
    """YOLOv8 wrapper for clothing object detection and shape analysis."""

    _model: YOLO | None = None

    @classmethod
    def get_model(cls) -> YOLO:
        if cls._model is None:
            model_path = settings.YOLO_MODEL_PATH
            logger.info("Loading YOLO model: %s", model_path)
            cls._model = YOLO(model_path)
        return cls._model

    @staticmethod
    def _classify_shape(aspect_ratio: float) -> str:
        if aspect_ratio > 1.5:
            return "แนวนอน (กว้าง)"
        if aspect_ratio < 0.7:
            return "แนวตั้ง (สูง)"
        return "สี่เหลี่ยมจัตุรัส"

    def detect(self, image_path: str, conf_threshold: float = 0.25) -> list[DetectionResult]:
        model = self.get_model()
        results = model(image_path, conf=conf_threshold, verbose=False)

        detections: list[DetectionResult] = []
        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                class_id = int(box.cls[0])
                class_name = model.names[class_id]
                confidence = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                width = x2 - x1
                height = y2 - y1
                aspect_ratio = round(width / max(height, 1), 2)

                detections.append(
                    DetectionResult(
                        class_name=class_name,
                        confidence=round(confidence, 3),
                        bbox=(x1, y1, x2, y2),
                        aspect_ratio=aspect_ratio,
                        shape_label=self._classify_shape(aspect_ratio),
                    )
                )

        return detections

    def detect_clothing(self, image_path: str, conf_threshold: float = 0.25) -> list[DetectionResult]:
        return [d for d in self.detect(image_path, conf_threshold) if d.class_name in CLOTHING_CLASSES]

    def draw_detections(self, image_path: str, detections: list[DetectionResult], output_path: str) -> str:
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Cannot read image: {image_path}")

        for det in detections:
            x1, y1, x2, y2 = det.bbox
            cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label = f"{det.class_name} {det.confidence:.0%}"
            cv2.putText(image, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        cv2.imwrite(output_path, image)
        return output_path
