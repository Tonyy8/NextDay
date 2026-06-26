from django.urls import path

from . import views

app_name = "detection"

urlpatterns = [
    path("", views.index, name="index"),
    path("results/<int:pk>/", views.results, name="results"),
    path("history/", views.history, name="history"),
]
