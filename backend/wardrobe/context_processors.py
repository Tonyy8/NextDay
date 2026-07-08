from django.conf import settings


def site_context(request):
    """Globals available in every template."""
    from wardrobe.user_preferences import get_font_size, get_ui_lang

    return {
        "mock_mode": getattr(settings, "MOCK_MODE", False),
        "mock_guest": getattr(settings, "MOCK_MODE", False)
        and request.session.get("mock_logged_out", True),
        "font_size": get_font_size(request),
        "ui_lang": get_ui_lang(request),
    }
