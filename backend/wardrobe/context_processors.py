from django.conf import settings


def site_context(request):
    """Globals available in every template."""
    return {
        "mock_mode": getattr(settings, "MOCK_MODE", False),
    }
