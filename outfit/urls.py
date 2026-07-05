from django.urls import path

from outfit import views

urlpatterns = [
    path("", views.home, name="home"),
    path("upload/", views.upload, name="upload"),
    path("closet/", views.closet, name="closet"),
    path("closet/<uuid:clothing_id>/delete/", views.closet_delete, name="closet_delete"),
    path("recommend/", views.recommend, name="recommend"),
]
