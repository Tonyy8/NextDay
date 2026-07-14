from django.contrib.auth import get_user_model
from django.core.management import call_command
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
        "allowed_categories": ["shirt", "blouse", "dress", "jumpsuit", "pants", "skirt", "jacket"],
        "description": "งานสังสรรค์ กึ่งทางการ",
    },
    {
        "name": "งานแต่งงาน",
        "slug": "wedding",
        "formality_level": 6,
        "icon": "💒",
        "allowed_categories": ["shirt", "blouse", "dress", "jumpsuit", "suit", "pants", "skirt", "jacket"],
        "description": "ทางการ — เดรส จั๊มสูท สูท (เลี่ยงชุดดำ/ขาวล้วน)",
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
    help = "Seed destinations, AI settings, demo users, and mock wardrobe images"

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-images",
            action="store_true",
            help="ข้ามการ import รูป mock wardrobe",
        )

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

        self._ensure_users()
        if not options["skip_images"]:
            call_command("import_mock_wardrobe")

        self.stdout.write(
            self.style.SUCCESS(
                "Demo ready.\n"
                "  Login mock: demo / (กดเข้าสู่ระบบในหน้า login)\n"
                "  Admin:      admin / admin123\n"
                "  Start:      uv run manage.py runserver"
            )
        )

    def _ensure_users(self):
        User = get_user_model()
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@nextday.local", "admin123")
            self.stdout.write(self.style.SUCCESS("Created admin / admin123"))
        else:
            self.stdout.write("Admin user already exists")

        if not User.objects.filter(username="demo").exists():
            User.objects.create_user("demo", "demo@nextday.app", "demo123")
            self.stdout.write(self.style.SUCCESS("Created demo / demo123"))
        else:
            self.stdout.write("Demo user already exists")
