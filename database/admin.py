from django.contrib import admin

from .models import AISettings, ClothingAnalysis, ClothingItem, Destination, FavoriteOutfit


@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    list_display = ["name", "formality_level", "allowed_categories", "icon"]
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ["name"]


@admin.register(AISettings)
class AISettingsAdmin(admin.ModelAdmin):
    list_display = ["confidence_threshold", "lab_min_delta", "lab_max_delta"]

    def has_add_permission(self, request):
        return not AISettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ClothingItem)
class ClothingItemAdmin(admin.ModelAdmin):
    list_display = [
        "id", "user", "garment_type", "part", "color_name_th",
        "formality", "confidence", "needs_review", "is_verified", "created_at",
    ]
    list_filter = ["part", "garment_type", "needs_review", "is_verified", "formality"]
    search_fields = ["color_name_th", "garment_type", "user__username"]


@admin.register(FavoriteOutfit)
class FavoriteOutfitAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "name", "destination", "match_score", "match_theory", "created_at"]
    list_filter = ["destination", "match_theory"]


@admin.register(ClothingAnalysis)
class ClothingAnalysisAdmin(admin.ModelAdmin):
    list_display = ["id", "class_name", "confidence", "primary_color_hex", "created_at"]
