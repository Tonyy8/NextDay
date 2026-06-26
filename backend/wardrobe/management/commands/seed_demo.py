from django.core.management.base import BaseCommand

from database.models import AISettings, Destination
from wardrobe.services.destination_profiles import DESTINATION_PROFILES


DESTINATIONS = [
    {
        "name": "อยู่บ้าน",
        "slug": "home",
        "formality_level": 1,
        "icon": "🏠",
        "allowed_categories": ["t_shirt", "shorts"],
        "description": "สบายๆ ที่บ้าน",
    },
    {
        "name": "ไปห้างสรรพสินค้า",
        "slug": "mall",
        "formality_level": 2,
        "icon": "🛍️",
        "allowed_categories": ["t_shirt", "shirt", "pants", "shorts"],
        "description": "สไตล์สบาย ลำลอง",
    },
    {
        "name": "ออฟฟิศ",
        "slug": "office",
        "formality_level": 4,
        "icon": "💼",
        "allowed_categories": ["shirt", "blouse", "pants", "skirt"],
        "description": "Smart Casual / Business Casual",
    },
    {
        "name": "งานเลี้ยง",
        "slug": "party",
        "formality_level": 5,
        "icon": "🎉",
        "allowed_categories": ["shirt", "blouse", "pants", "skirt", "jacket"],
        "description": "งานสังสรรค์ กึ่งทางการ",
    },
    {
        "name": "งานแต่งงาน",
        "slug": "wedding",
        "formality_level": 6,
        "icon": "💒",
        "allowed_categories": ["shirt", "blouse", "pants", "skirt", "jacket"],
        "description": "ทางการ สุภาพเรียบร้อย",
    },
    {
        "name": "ออกกำลังกาย",
        "slug": "sport",
        "formality_level": 1,
        "icon": "🏃",
        "allowed_categories": ["t_shirt", "shorts"],
        "description": "Active wear",
    },
]


class Command(BaseCommand):
    help = "Seed destinations (Matrix A) and AI settings"

    def handle(self, *args, **options):
        for d in DESTINATIONS:
            profile = DESTINATION_PROFILES.get(d["slug"], {})
            defaults = {
                **d,
                "weather": profile.get("weather", "mild"),
                "style": profile.get("style", "casual"),
                "garment_rules": profile.get("garment_rules", {}),
            }
            Destination.objects.update_or_create(slug=d["slug"], defaults=defaults)
        AISettings.objects.get_or_create(pk=1)
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(DESTINATIONS)} destinations + AI settings"))
