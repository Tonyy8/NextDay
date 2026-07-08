from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth import login, logout
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import url_has_allowed_host_and_scheme, urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.http import require_http_methods

from .forms import ForgotPasswordForm, LoginForm, RegisterForm, ResetPasswordForm

User = get_user_model()


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


def _get_user_by_email(email: str):
    email = email.strip().lower()
    user = User.objects.filter(username__iexact=email).first()
    if user:
        return user
    return User.objects.filter(email__iexact=email).first()


def _reset_password_path(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return reverse("accounts:reset_password", kwargs={"uidb64": uid, "token": token})


@require_http_methods(["GET", "POST"])
def forgot_password_view(request):
    form = ForgotPasswordForm()
    if request.method == "POST":
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].strip()
            user = _get_user_by_email(email)
            reset_url = None
            if user:
                reset_url = request.build_absolute_uri(_reset_password_path(user))
            elif settings.MOCK_MODE:
                user, _ = User.objects.get_or_create(
                    username=email.lower(),
                    defaults={"email": email},
                )
                reset_url = request.build_absolute_uri(_reset_password_path(user))
            return render(request, "pages/auth/forgot_password_done.html", {
                "email": email,
                "reset_url": reset_url,
                "show_reset_link": bool(reset_url and (settings.MOCK_MODE or settings.DEBUG)),
            })
    return render(request, "pages/auth/forgot_password.html", {
        "form": form,
        "active_tab": "login",
    })


@require_http_methods(["GET", "POST"])
def reset_password_view(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is None or not default_token_generator.check_token(user, token):
        messages.error(request, "ลิงก์รีเซ็ตรหัสผ่านไม่ถูกต้องหรือหมดอายุแล้ว")
        return redirect("accounts:forgot_password")

    form = ResetPasswordForm()
    if request.method == "POST":
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            user.set_password(form.cleaned_data["password"])
            user.save(update_fields=["password"])
            messages.success(request, "ตั้งรหัสผ่านใหม่สำเร็จแล้ว กรุณาเข้าสู่ระบบ")
            return redirect("accounts:login")

    return render(request, "pages/auth/reset_password.html", {
        "form": form,
        "active_tab": "login",
    })


def logout_view(request):
    if settings.MOCK_MODE:
        request.session["mock_logged_out"] = True
        messages.info(request, "ออกจากระบบแล้ว")
        return redirect("accounts:login")
    logout(request)
    messages.info(request, "ออกจากระบบแล้ว")
    return redirect("accounts:login")
