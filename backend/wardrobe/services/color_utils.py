import colorsys
import math

import cv2
import numpy as np


def hex_to_rgb(hex_code: str) -> tuple[int, int, int]:
    h = hex_code.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def rgb_to_lab(r: int, g: int, b: int) -> tuple[float, float, float]:
    bgr = np.uint8([[[b, g, r]]])
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    l, a, bb = lab[0][0]
    return float(l), float(a), float(bb)


def lab_distance(l1, a1, b1, l2, a2, b2) -> float:
    return math.sqrt((l1 - l2) ** 2 + (a1 - a2) ** 2 + (b1 - b2) ** 2)


def rgb_to_hue(r: int, g: int, b: int) -> float:
    h, _, _ = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    return h * 360


def thai_color_name(hex_code: str) -> str:
    r, g, b = hex_to_rgb(hex_code)
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    h_deg = h * 360

    if v < 0.15:
        return "ดำ"
    if v > 0.92 and s < 0.12:
        return "ขาว"
    if s < 0.12:
        return "เทา" if v < 0.7 else "ครีม"

    if h_deg < 15 or h_deg >= 345:
        return "แดง"
    if h_deg < 40:
        return "ส้ม"
    if h_deg < 65:
        return "เหลือง"
    if h_deg < 160:
        return "เขียว"
    if h_deg < 200:
        return "ฟ้า"
    if h_deg < 260:
        return "น้ำเงิน"
    if h_deg < 300:
        return "ม่วง"
    return "ชมพู"


def itten_relation(hue1: float, hue2: float) -> str:
    diff = abs(hue1 - hue2) % 360
    if diff > 180:
        diff = 360 - diff
    if diff <= 20:
        return "Monochromatic"
    if 25 <= diff <= 45:
        return "Analogous (Itten)"
    if 55 <= diff <= 75:
        return "Triadic (Itten)"
    if 160 <= diff <= 200:
        return "Complementary (Itten)"
    return "Split-Complementary"


def munsell_balance(l1, l2) -> str:
    diff = abs(l1 - l2)
    if diff <= 15:
        return "Munsell: สมดุล"
    if diff <= 35:
        return "Munsell: คอนทราสต์พอดี"
    return "Munsell: คอนทราสต์สูง"
