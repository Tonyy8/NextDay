from django.urls import path

from . import views

app_name = "wardrobe"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("upload/", views.upload, name="upload"),
    path("upload/result/", views.upload_result, name="upload_result"),
    path("wardrobe/", views.wardrobe_list, name="wardrobe"),
    path("wardrobe/<int:pk>/edit/", views.wardrobe_edit, name="edit"),
    path("wardrobe/<int:pk>/delete/", views.wardrobe_delete, name="delete"),
    path("verify/<int:pk>/", views.verify, name="verify"),
    path("outfit/", views.outfit_builder, name="outfit"),
    path("outfit/manual/", views.manual_outfit, name="manual_outfit"),
    path("outfit/save/", views.save_outfit, name="save_outfit"),
    path("favorites/", views.favorites, name="favorites"),
    path("favorites/<int:pk>/delete/", views.delete_favorite, name="delete_favorite"),
    path("community/", views.community, name="community"),
    path("profile/", views.profile, name="profile"),
    path("feedback/", views.feedback, name="feedback"),
]
