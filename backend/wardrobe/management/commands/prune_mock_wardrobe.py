from django.core.management.base import BaseCommand

from wardrobe.sample_import import MANIFEST_PATH, prune_manifest_entries


class Command(BaseCommand):
    help = "เก็บเฉพาะเสื้อผ้าที่มีไฟล์รูปจริง แล้วเซฟ manifest.json"

    def handle(self, *args, **options):
        before = 0
        if MANIFEST_PATH.is_file():
            import json

            before = len(json.loads(MANIFEST_PATH.read_text(encoding="utf-8")))
        kept = prune_manifest_entries(save_curated=True)
        removed = before - len(kept)
        self.stdout.write(
            self.style.SUCCESS(
                f"saved {len(kept)} items ({removed} removed without image) -> {MANIFEST_PATH}"
            )
        )
