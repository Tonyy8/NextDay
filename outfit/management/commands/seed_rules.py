from django.core.management.base import BaseCommand

from outfit.models import DressRule, Location

SEED = [
    {
        "slug": "wedding",
        "name": "งานแต่ง",
        "description": "งานแต่งงาน / พิธีการ",
        "rules": [
            {"temp_min": 0, "temp_max": 45, "allowed_styles": ["formal", "elegant"],
             "forbidden_rules": ["no_black_solid", "no_shorts", "no_sporty"], "formality_min": 0.8},
        ],
    },
    {
        "slug": "cafe",
        "name": "คาเฟ่",
        "description": "ออกไปคาเฟ่ / ชิล ๆ",
        "rules": [
            {"temp_min": 0, "temp_max": 28, "allowed_styles": ["casual", "smart_casual"],
             "forbidden_rules": ["no_sporty"], "formality_min": 0.3},
            {"temp_min": 28, "temp_max": 45, "allowed_styles": ["casual", "light"],
             "forbidden_rules": ["no_sporty"], "formality_min": 0.2},
        ],
    },
    {
        "slug": "office",
        "name": "ทำงาน",
        "description": "ออฟฟิศ / ประชุม",
        "rules": [
            {"temp_min": 0, "temp_max": 45, "allowed_styles": ["formal", "business"],
             "forbidden_rules": ["no_shorts", "no_sporty", "no_revealing"], "formality_min": 0.7},
        ],
    },
    {
        "slug": "beach",
        "name": "ทะเล",
        "description": "ชายหาด / ทริปทะเล",
        "rules": [
            {"temp_min": 25, "temp_max": 45, "allowed_styles": ["casual", "beach", "sporty"],
             "forbidden_rules": ["no_black_solid"], "formality_min": 0.1},
        ],
    },
    {
        "slug": "party",
        "name": "งานเลี้ยง",
        "description": "ปาร์ตี้ / งานสังสรรค์",
        "rules": [
            {"temp_min": 0, "temp_max": 45, "allowed_styles": ["party", "smart", "street"],
             "forbidden_rules": ["no_sporty"], "formality_min": 0.5},
        ],
    },
]


class Command(BaseCommand):
    help = "Seed locations + Matrix A dress rules"

    def handle(self, *args, **options):
        for row in SEED:
            loc, _ = Location.objects.update_or_create(
                slug=row["slug"],
                defaults={"name": row["name"], "description": row["description"]},
            )
            DressRule.objects.filter(location=loc).delete()
            for rule in row["rules"]:
                DressRule.objects.create(location=loc, **rule)
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(SEED)} locations + rules"))
