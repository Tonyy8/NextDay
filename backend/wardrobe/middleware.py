from django.conf import settings


class MockUser:
    """Lightweight stand-in for an authenticated user in MOCK_MODE."""

    username = "demo"
    email = "demo@nextday.app"
    is_authenticated = True
    is_active = True
    is_staff = False
    is_superuser = False
    is_anonymous = False
    pk = 1
    id = 1

    def __str__(self):
        return self.username

    @property
    def is_anonymous_user(self):
        return False


class MockAuthMiddleware:
    """Auto-login a demo user when MOCK_MODE is on."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if getattr(settings, "MOCK_MODE", False):
            request.user = MockUser()
        return self.get_response(request)
