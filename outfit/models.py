import uuid

from django.db import models

from outfit.constants import GARMENT_CHOICES


class Location(models.Model):
    """สถานที่ที่ผู้ใช้เลือก — ใช้สร้าง Matrix A ร่วมกับสภาพอากาศ."""

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=64)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class DressRule(models.Model):
    """
    Matrix A — เกณฑ์มาตรฐาน (Simple Table)
    กำหนดว่าสถานที่ + ช่วงอุณหภูมิ ควร/ห้ามแต่งตัวอย่างไร
    """

    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="rules")
    temp_min = models.FloatField(help_text="อุณหภูมิต่ำสุด (°C)")
    temp_max = models.FloatField(help_text="อุณหภูมิสูงสุด (°C)")
    allowed_styles = models.JSONField(default=list)
    forbidden_rules = models.JSONField(
        default=list,
        help_text='เช่น ["no_black_solid", "no_shorts", "no_sporty"]',
    )
    formality_min = models.FloatField(default=0.0, help_text="0=ลำลอง, 1=ทางการมาก")

    class Meta:
        ordering = ["location", "temp_min"]

    def __str__(self):
        return f"{self.location.name} ({self.temp_min}-{self.temp_max}°C)"


class Clothing(models.Model):
    """
    Matrix B — ตู้เสื้อผ้าจริงของผู้ใช้
    เก็บประเภท (Top/Bottom) และเฉดสีหลักจาก OpenCV K-Means
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(db_index=True)
    image = models.ImageField(upload_to="closet/%Y/%m/")
    name = models.CharField(max_length=128, blank=True)
    garment_type = models.CharField(max_length=16, choices=GARMENT_CHOICES)
    category = models.CharField(max_length=32, blank=True)
    dominant_color_hex = models.CharField(max_length=7, default="#808080")
    dominant_color_rgb = models.JSONField(default=list)
    color_name = models.CharField(max_length=32, blank=True)
    preference_score = models.FloatField(
        default=0.5,
        help_text="CBF — ยิ่งใส่บ่อย/ถูกใจ คะแนนสูงขึ้น",
    )
    wear_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name or f"{self.get_garment_type_display()} {self.color_name}"
