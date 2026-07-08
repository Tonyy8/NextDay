from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods

from .forms import LoginForm, RegisterForm


def _safe_next_url(request):
    nxt = request.POST.get("next") or request.GET.get("next")
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        return nxt
    return None


def _mock_login_session(request, display_name: str, email: str):
    request.session["mock_logged_out"] = False
    request.session["mock_profile"] = {
        "display_name": display_name,
        "email": email,
    }
    request.session.pop("mock_deleted_pks", None)
    request.session.pop("mock_uploaded_items", None)
    request.session.modified = True


def home_view(request):
    if settings.MOCK_MODE and not request.session.get("mock_logged_out", True):
        return redirect("wardrobe:dashboard")
    return redirect("accounts:login")


@require_http_methods(["GET", "POST"])
def login_view(request):
    next_url = _safe_next_url(request)

    if settings.MOCK_MODE:
        if request.method == "POST":
            email = (request.POST.get("email") or "demo").strip() or "demo"
            display = email.split("@")[0] if email else "demo"
            _mock_login_session(request, display, email if "@" in email else f"{email}@nextday.app")
            messages.success(request, "เข้าสู่ระบบสำเร็จ")
            return redirect(next_url or "wardrobe:dashboard")
        if not request.session.get("mock_logged_out", True):
            return redirect(next_url or "wardrobe:dashboard")
        return render(request, "pages/auth/login.html", {
            "form": LoginForm(),
            "active_tab": "login",
            "next": next_url or "",
        })

    if request.user.is_authenticated:
        return redirect(next_url or "wardrobe:dashboard")

    form = LoginForm()
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            login(request, form.user)
            messages.success(request, "เข้าสู่ระบบสำเร็จ")
            return redirect(next_url or "wardrobe:dashboard")

    return render(request, "pages/auth/login.html", {
        "form": form,
        "active_tab": "login",
        "next": next_url or "",
    })


@require_http_methods(["GET", "POST"])
def register_view(request):
    next_url = _safe_next_url(request)

    if settings.MOCK_MODE:
        if request.method == "POST":
            email = (request.POST.get("email") or "demo").strip() or "demo"
            display = email.split("@")[0] if email else "demo"
            _mock_login_session(request, display, email if "@" in email else f"{email}@nextday.app")
            messages.success(request, "สมัครสมาชิกสำเร็จ ยินดีต้อนรับสู่ NEXTDAY")
            return redirect(next_url or "wardrobe:dashboard")
        if not request.session.get("mock_logged_out", True):
            return redirect(next_url or "wardrobe:dashboard")
        return render(request, "pages/auth/register.html", {
            "form": RegisterForm(),
            "active_tab": "register",
            "next": next_url or "",
        })

    if request.user.is_authenticated:
        return redirect(next_url or "wardrobe:dashboard")

    form = RegisterForm()
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "สมัครสมาชิกสำเร็จ ยินดีต้อนรับสู่ NEXTDAY")
            return redirect(next_url or "wardrobe:dashboard")

    return render(request, "pages/auth/register.html", {
        "form": form,
        "active_tab": "register",
        "next": next_url or "",
    })


def logout_view(request):
    if settings.MOCK_MODE:
        request.session["mock_logged_out"] = True
        messages.info(request, "ออกจากระบบแล้ว")
        return redirect("accounts:login")
    logout(request)
    messages.info(request, "ออกจากระบบแล้ว")
    return redirect("accounts:login")
