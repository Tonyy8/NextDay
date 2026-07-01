from django.conf import settings


def site_context(request):
    """Globals available in every template."""
    return {
        "mock_mode": getattr(settings, "MOCK_MODE", False),
        "mock_guest": getattr(settings, "MOCK_MODE", False) and request.session.get("mock_logged_out"),
    }
