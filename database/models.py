from django.contrib.auth.models import User
from django.db import models

from database.garment_catalog import (
    BOTTOM_TYPES,
    GARMENT_CATEGORY_GROUPS,
    GARMENT_TYPES,
    ONE_PIECE_TYPES,
    TOP_TYPES,
    get_base_garment_type,
    grouped_choices,
    infer_part,
)

PART_CHOICES = [
    ("top", "ท่อนบน"),
    ("bottom", "ท่อนล่าง"),
]

FABRIC_THICKNESS_CHOICES = [
    ("thin", "บาง"),
    ("medium", "ปานกลาง"),
    ("thick", "หนา"),
]

WEATHER_CHOICES = [
    ("hot", "ร้อน"),
    ("mild", "อุ่นสบาย"),
    ("cool", "เย็น/แอร์"),
]

STYLE_CHOICES = [
    ("casual", "สบายๆ"),
    ("smart_casual", "สมาร์ทแคชชวล"),
    ("formal", "ทางการ"),
    ("sporty", "กีฬา"),
]


class Destination(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    formality_level = models.IntegerField(help_text="ระดับความสุภาพ 1-6")
    allowed_categories = models.JSONField(default=list, help_text="ประเภทเสื้อผ้าที่อนุญาต")
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=10, default="📍")
    weather = models.CharField(max_length=10, choices=WEATHER_CHOICES, default="mild")
    style = models.CharField(max_length=20, choices=STYLE_CHOICES, default="casual")
    garment_rules = models.JSONField(default=dict, blank=True, help_text="Matrix A: เกณฑ์ต่อประเภทเสื้อผ้า")

    class Meta:
        db_table = "destinations"
        verbose_name = "สถานที่/โอกาส"
        verbose_name_plural = "สถานที่/โอกาส"
        ordering = ["formality_level"]

    def __str__(self):
        return self.name


class AISettings(models.Model):
    confidence_threshold = models.FloatField(default=0.6, help_text="เกณฑ์ความมั่นใจขั้นต่ำ")
    lab_min_delta = models.FloatField(default=12.0, help_text="Goldilocks: ระยะสีต่ำสุด")
    lab_max_delta = models.FloatField(default=45.0, help_text="Goldilocks: ระยะสีสูงสุด")

    class Meta:
        db_table = "ai_settings"
        verbose_name = "ตั้งค่า AI"
        verbose_name_plural = "ตั้งค่า AI"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "ตั้งค่าระบบ AI"


class ClothingItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="clothing_items")
    image = models.ImageField(upload_to="wardrobe/%Y/%m/%d/")
    cropped_image = models.ImageField(upload_to="wardrobe/crops/%Y/%m/%d/", blank=True, null=True)

    part = models.CharField(max_length=10, choices=PART_CHOICES)
    garment_type = models.CharField(max_length=32, choices=GARMENT_TYPES)
    formality = models.IntegerField(default=3, help_text="ระดับความสุภาพ 1-6")
    fabric_thickness = models.CharField(
        max_length=10,
        choices=FABRIC_THICKNESS_CHOICES,
        default="medium",
        help_text="ความหนาผ้า",
    )

    confidence = models.FloatField(default=0.0)
    needs_review = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)

    primary_color_hex = models.CharField(max_length=7)
    color_name_th = models.CharField(max_length=50, blank=True)
    dominant_colors = models.JSONField(default=list)
    lab_l = models.FloatField(default=0)
    lab_a = models.FloatField(default=0)
    lab_b = models.FloatField(default=0)

    bbox_x1 = models.IntegerField(default=0)
    bbox_y1 = models.IntegerField(default=0)
    bbox_x2 = models.IntegerField(default=0)
    bbox_y2 = models.IntegerField(default=0)
    aspect_ratio = models.FloatField(default=1.0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "clothing_items"
        ordering = ["-created_at"]
        verbose_name = "เสื้อผ้า"
        verbose_name_plural = "เสื้อผ้า"

    def __str__(self):
        return f"{self.get_garment_type_display()} - {self.color_name_th} ({self.user.username})"

    @property
    def bbox(self):
        return self.bbox_x1, self.bbox_y1, self.bbox_x2, self.bbox_y2

    @property
    def display_name(self):
        return f"{self.get_garment_type_display()} สี{self.color_name_th}"


class FavoriteOutfit(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favorite_outfits")
    destination = models.ForeignKey(Destination, on_delete=models.SET_NULL, null=True)
    top_item = models.ForeignKey(ClothingItem, on_delete=models.CASCADE, related_name="outfits_as_top")
    bottom_item = models.ForeignKey(ClothingItem, on_delete=models.CASCADE, related_name="outfits_as_bottom")
    name = models.CharField(max_length=100, blank=True)
    match_score = models.FloatField(default=0.0)
    match_theory = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "favorite_outfits"
        ordering = ["-created_at"]
        verbose_name = "ชุดโปรด"
        verbose_name_plural = "ชุดโปรด"

    def __str__(self):
        return self.name or f"ชุด #{self.pk}"


# Legacy model kept for backward compatibility
class ClothingAnalysis(models.Model):
    image = models.ImageField(upload_to="uploads/%Y/%m/%d/")
    annotated_image = models.ImageField(upload_to="results/%Y/%m/%d/", blank=True, null=True)
    class_name = models.CharField(max_length=100)
    confidence = models.FloatField()
    bbox_x1 = models.IntegerField()
    bbox_y1 = models.IntegerField()
    bbox_x2 = models.IntegerField()
    bbox_y2 = models.IntegerField()
    aspect_ratio = models.FloatField()
    shape_label = models.CharField(max_length=50)
    primary_color_hex = models.CharField(max_length=7)
    primary_color_rgb = models.CharField(max_length=20)
    dominant_colors = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "clothing_analysis"
        ordering = ["-created_at"]
        verbose_name = "การวิเคราะห์เสื้อผ้า (Legacy)"
        verbose_name_plural = "การวิเคราะห์เสื้อผ้า (Legacy)"

    def __str__(self):
        return f"{self.class_name} - {self.primary_color_hex}"
