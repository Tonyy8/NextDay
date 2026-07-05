from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from outfit.constants import GARMENT_CHOICES, LOCATIONS
from outfit.ml.pipeline import scan_clothing
from outfit.models import Clothing, Location
from outfit.services.matrix_a import build_matrix_a
from outfit.services.recommendation import recommend_top3
from outfit.services.weather import fetch_weather


def _uid():
    return settings.DEMO_USER_ID


def home(request):
    count = Clothing.objects.filter(user_id=_uid()).count()
    return render(request, "outfit/home.html", {"closet_count": count})


def upload(request):
    if request.method == "POST":
        image = request.FILES.get("image")
        if not image:
            messages.error(request, "เลือกรูปก่อน")
            return render(request, "outfit/upload.html", {"garment_choices": GARMENT_CHOICES})

        data = image.read()
        try:
            scan = scan_clothing(data)
        except Exception as e:
            messages.error(request, f"สแกนไม่สำเร็จ: {e}")
            return render(request, "outfit/upload.html", {"garment_choices": GARMENT_CHOICES})

        image.seek(0)

        name = (request.POST.get("name") or "").strip()
        garment_type = request.POST.get("garment_type") or scan.garment_type

        Clothing.objects.create(
            user_id=_uid(),
            image=image,
            name=name or f"{scan.color_name} {scan.category}",
            garment_type=garment_type,
            category=scan.category,
            dominant_color_hex=scan.dominant_color_hex,
            dominant_color_rgb=scan.dominant_color_rgb,
            color_name=scan.color_name,
        )
        messages.success(
            request,
            f"บันทึกแล้ว: {scan.color_name} · {garment_type} "
            f"(YOLO: {'ใช่' if scan.yolo_used else 'fallback'})",
        )
        return redirect("closet")

    return render(request, "outfit/upload.html", {"garment_choices": GARMENT_CHOICES})


def closet(request):
    items = Clothing.objects.filter(user_id=_uid())
    return render(request, "outfit/closet.html", {"items": items})


@require_POST
def closet_delete(request, clothing_id):
    item = get_object_or_404(Clothing, id=clothing_id, user_id=_uid())
    item.image.delete(save=False)
    item.delete()
    messages.success(request, "ลบแล้ว")
    return redirect("closet")


def recommend(request):
    locations = Location.objects.all()
    weather = fetch_weather()
    results = None
    selected = request.GET.get("location", "cafe")

    if request.method == "POST" or request.GET.get("run"):
        selected = request.GET.get("location") or request.POST.get("location", "cafe")
        try:
            matrix_a = build_matrix_a(selected, weather)
            results = recommend_top3(_uid(), matrix_a)
            if not results:
                messages.warning(request, "ไม่พบชุดที่ผ่านเกณฑ์ — เพิ่มเสื้อ Top + Bottom ในตู้")
        except Exception as e:
            messages.error(request, str(e))

    return render(request, "outfit/recommend.html", {
        "locations": locations,
        "location_choices": LOCATIONS,
        "selected": selected,
        "weather": weather,
        "results": results,
        "cbf_weight": 60,
        "color_weight": 40,
    })
