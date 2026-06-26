from django import forms
from django.contrib.auth.models import User


class LoginForm(forms.Form):
    email = forms.CharField(
        label="อีเมล",
        widget=forms.TextInput(
            attrs={
                "class": "auth-input",
                "placeholder": "ใส่อะไรก็ได้",
                "autocomplete": "username",
            }
        ),
    )
    password = forms.CharField(
        label="รหัสผ่าน",
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "auth-input",
                "placeholder": "ใส่อะไรก็ได้",
                "autocomplete": "current-password",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        self.user = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        username = (cleaned.get("email") or "guest").strip().lower() or "guest"
        user, _ = User.objects.get_or_create(
            username=username,
            defaults={"email": username if "@" in username else f"{username}@nextday.local"},
        )
        self.user = user
        return cleaned


class RegisterForm(forms.Form):
    email = forms.EmailField(
        label="อีเมล",
        widget=forms.EmailInput(
            attrs={
                "class": "auth-input",
                "placeholder": "example@email.com",
                "autocomplete": "email",
            }
        ),
    )
    password = forms.CharField(
        label="รหัสผ่าน",
        min_length=8,
        widget=forms.PasswordInput(
            attrs={
                "class": "auth-input",
                "placeholder": "อย่างน้อย 8 ตัวอักษร",
                "autocomplete": "new-password",
            }
        ),
    )
    password_confirm = forms.CharField(
        label="ยืนยันรหัสผ่าน",
        widget=forms.PasswordInput(
            attrs={
                "class": "auth-input",
                "placeholder": "กรอกรหัสผ่านอีกครั้ง",
                "autocomplete": "new-password",
            }
        ),
    )

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(username=email).exists():
            raise forms.ValidationError("อีเมลนี้ถูกใช้งานแล้ว")
        return email

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") != cleaned.get("password_confirm"):
            raise forms.ValidationError("รหัสผ่านไม่ตรงกัน")
        return cleaned

    def save(self):
        email = self.cleaned_data["email"]
        password = self.cleaned_data["password"]
        return User.objects.create_user(username=email, email=email, password=password)
