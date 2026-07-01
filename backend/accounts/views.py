from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import LoginForm, RegisterForm


def home_view(request):
    if settings.MOCK_MODE:
        return redirect("wardrobe:dashboard")
    return redirect("accounts:login")


@require_http_methods(["GET", "POST"])
def login_view(request):
    if settings.MOCK_MODE:
        if request.method == "POST":
            request.session.pop("mock_logged_out", None)
            messages.success(request, "เข้าสู่ระบบสำเร็จ (Mockup)")
            return redirect("wardrobe:dashboard")
        return redirect("wardrobe:dashboard")

    if request.user.is_authenticated:
        return redirect("wardrobe:dashboard")

    form = LoginForm()
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            login(request, form.user)
            messages.success(request, "เข้าสู่ระบบสำเร็จ")
            return redirect("wardrobe:dashboard")

    return render(request, "accounts/login.html", {"form": form, "active_tab": "login"})


@require_http_methods(["GET", "POST"])
def register_view(request):
    if settings.MOCK_MODE:
        if request.method == "POST":
            request.session.pop("mock_logged_out", None)
            messages.success(request, "สมัครสมาชิกสำเร็จ (Mockup)")
            return redirect("wardrobe:dashboard")
        return redirect("wardrobe:dashboard")

    if request.user.is_authenticated:
        return redirect("wardrobe:dashboard")

    form = RegisterForm()
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "สมัครสมาชิกสำเร็จ ยินดีต้อนรับสู่ NEXTDAY")
            return redirect("wardrobe:dashboard")

    return render(request, "accounts/register.html", {"form": form, "active_tab": "register"})


def logout_view(request):
    if settings.MOCK_MODE:
        request.session.pop("mock_logged_out", None)
        messages.info(request, "ออกจากระบบแล้ว (Mockup)")
        return redirect("wardrobe:dashboard")
    logout(request)
    messages.info(request, "ออกจากระบบแล้ว")
    return redirect("accounts:login")
