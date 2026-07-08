from django.conf import settings


class MockUser:
    """Lightweight stand-in for an authenticated user in MOCK_MODE."""

    is_authenticated = True
    is_active = True
    is_staff = False
    is_superuser = False
    is_anonymous = False
    pk = 1
    id = 1

    def __init__(self, username="demo", email="demo@nextday.app"):
        self.username = username
        self.email = email

    def __str__(self):
        return self.username

    @property
    def is_anonymous_user(self):
        return False


class MockAuthMiddleware:
    """Auto-login demo user in MOCK_MODE after mock login succeeds."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if getattr(settings, "MOCK_MODE", False):
            if not request.session.get("mock_logged_out", True):
                profile = request.session.get("mock_profile", {})
                username = profile.get("display_name", "demo")
                email = profile.get("email", "demo@nextday.app")
                request.user = MockUser(username=username, email=email)
        return self.get_response(request)


class MockLoginGateMiddleware:
    """In MOCK_MODE, /app/* requires mock login (session) before access."""

    _PUBLIC_PREFIXES = ("/login/", "/register/", "/logout/", "/static/", "/health/", "/admin/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if getattr(settings, "MOCK_MODE", False):
            path = request.path
            if path.startswith("/app/") and not request.user.is_authenticated:
                from django.shortcuts import redirect
                from django.urls import reverse
                from urllib.parse import urlencode

                login_url = reverse("accounts:login")
                return redirect(f"{login_url}?{urlencode({'next': path})}")
            if path.startswith("/app/") and any(path.startswith(p) for p in self._PUBLIC_PREFIXES):
                pass
        return self.get_response(request)
