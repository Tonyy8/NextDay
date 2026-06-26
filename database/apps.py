from django.apps import AppConfig


class DatabaseConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "database"
    verbose_name = "ฐานข้อมูล"

    def ready(self):
        import database.signals  # noqa: F401
