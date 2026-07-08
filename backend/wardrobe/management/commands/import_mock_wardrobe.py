from django.core.management.base import BaseCommand

from wardrobe.sample_import import DEFAULT_SOURCE, MANIFEST_PATH, STATIC_DIR, build_manifest


class Command(BaseCommand):
    help = "นำเข้ารูปเสื้อผ้าตัวอย่างจากโฟลเดอร์ mock → static/mock/wardrobe + manifest.json"

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            type=str,
            default=str(DEFAULT_SOURCE),
            help="โฟลเดอร์ต้นทางที่มีรูปตัวอย่าง",
        )

    def handle(self, *args, **options):
        source = options["source"]
        entries = build_manifest(source)
        self.stdout.write(
            self.style.SUCCESS(
                f"imported {len(entries)} items -> {STATIC_DIR}\nmanifest: {MANIFEST_PATH}"
            )
        )
        for rec in entries:
            self.stdout.write(
                f"  pk{rec['pk']:02d} {rec['garment_type']:8} {rec['color_name_th']:6} ← {rec['source_name'][:50]}"
            )
