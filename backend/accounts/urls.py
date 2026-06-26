from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.home_view, name="login"),
    path("login/", views.login_view),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),
]
