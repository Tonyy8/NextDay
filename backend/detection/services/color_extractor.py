import logging
from dataclasses import dataclass

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ColorResult:
    hex_code: str
    rgb: tuple[int, int, int]
    percentage: float


class ColorExtractor:
    """Extract dominant colors from images using OpenCV."""

    @staticmethod
    def _rgb_to_hex(r: int, g: int, b: int) -> str:
        return f"#{r:02X}{g:02X}{b:02X}"

    def extract_dominant_colors(
        self,
        image_path: str,
        k: int = 3,
        bbox: tuple[int, int, int, int] | None = None,
    ) -> list[ColorResult]:
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Cannot read image: {image_path}")

        if bbox:
            x1, y1, x2, y2 = bbox
            image = image[y1:y2, x1:x2]

        if image.size == 0:
            return []

        pixels = image.reshape(-1, 3).astype(np.float32)
        k = min(k, len(pixels))

        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
        _, labels, centers = cv2.kmeans(pixels, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)

        label_counts = np.bincount(labels.flatten())
        total = label_counts.sum()

        colors: list[ColorResult] = []
        for i, center in enumerate(centers):
            b, g, r = map(int, center)
            percentage = round(label_counts[i] / total * 100, 1)
            colors.append(ColorResult(hex_code=self._rgb_to_hex(r, g, b), rgb=(r, g, b), percentage=percentage))

        colors.sort(key=lambda c: c.percentage, reverse=True)
        return colors

    def extract_primary_color(
        self,
        image_path: str,
        bbox: tuple[int, int, int, int] | None = None,
    ) -> ColorResult | None:
        colors = self.extract_dominant_colors(image_path, k=1, bbox=bbox)
        return colors[0] if colors else None
