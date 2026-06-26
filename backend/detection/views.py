import os
import uuid

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import ImageUploadForm
from database.models import ClothingAnalysis


@login_required
@require_http_methods(["GET", "POST"])
def index(request):
    form = ImageUploadForm()
    recent_analyses = ClothingAnalysis.objects.all()[:10]

    if request.method == "POST":
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                results = _process_image(form.cleaned_data["image"])
                messages.success(request, f"วิเคราะห์สำเร็จ พบ {len(results)} วัตถุ")
                if results:
                    return redirect("detection:results", pk=results[0].pk)
                return redirect("detection:index")
            except Exception as exc:
                messages.error(request, f"เกิดข้อผิดพลาด: {exc}")

    return render(request, "detection/index.html", {"form": form, "recent_analyses": recent_analyses})


@login_required
def results(request, pk):
    analysis = get_object_or_404(ClothingAnalysis, pk=pk)
    related = ClothingAnalysis.objects.filter(
        image=analysis.image,
    ).exclude(pk=pk)
    return render(request, "detection/results.html", {"analysis": analysis, "related": related})


@login_required
def history(request):
    analyses = ClothingAnalysis.objects.all()
    return render(request, "detection/history.html", {"analyses": analyses})


def _process_image(uploaded_file) -> list[ClothingAnalysis]:
    from .services import ColorExtractor, YOLODetector  # lazy: heavy AI deps

    detector = YOLODetector()
    color_extractor = ColorExtractor()

    temp_name = f"temp_{uuid.uuid4().hex}_{uploaded_file.name}"
    temp_path = os.path.join(settings.MEDIA_ROOT, "uploads", temp_name)
    os.makedirs(os.path.dirname(temp_path), exist_ok=True)

    with open(temp_path, "wb") as f:
        for chunk in uploaded_file.chunks():
            f.write(chunk)

    detections = detector.detect(temp_path)
    saved: list[ClothingAnalysis] = []

    if detections:
        annotated_name = f"annotated_{uuid.uuid4().hex}.jpg"
        annotated_path = os.path.join(settings.MEDIA_ROOT, "results", annotated_name)
        os.makedirs(os.path.dirname(annotated_path), exist_ok=True)
        detector.draw_detections(temp_path, detections, annotated_path)

    for det in detections:
        colors = color_extractor.extract_dominant_colors(temp_path, k=3, bbox=det.bbox)
        primary = colors[0] if colors else None

        analysis = ClothingAnalysis(
            class_name=det.class_name,
            confidence=det.confidence,
            bbox_x1=det.bbox[0],
            bbox_y1=det.bbox[1],
            bbox_x2=det.bbox[2],
            bbox_y2=det.bbox[3],
            aspect_ratio=det.aspect_ratio,
            shape_label=det.shape_label,
            primary_color_hex=primary.hex_code if primary else "#000000",
            primary_color_rgb=str(primary.rgb) if primary else "(0, 0, 0)",
            dominant_colors=[
                {"hex": c.hex_code, "rgb": c.rgb, "percentage": c.percentage} for c in colors
            ],
        )
        with open(temp_path, "rb") as img_file:
            analysis.image.save(uploaded_file.name, ContentFile(img_file.read()), save=False)
        if detections:
            with open(annotated_path, "rb") as ann_file:
                analysis.annotated_image.save(annotated_name, ContentFile(ann_file.read()), save=False)
        analysis.save()
        saved.append(analysis)

    if not saved:
        analysis = ClothingAnalysis(
            class_name="ไม่พบวัตถุ",
            confidence=0.0,
            bbox_x1=0,
            bbox_y1=0,
            bbox_x2=0,
            bbox_y2=0,
            aspect_ratio=0.0,
            shape_label="-",
            primary_color_hex="#000000",
            primary_color_rgb="(0, 0, 0)",
            dominant_colors=[],
        )
        with open(temp_path, "rb") as img_file:
            analysis.image.save(uploaded_file.name, ContentFile(img_file.read()), save=False)
        analysis.save()
        saved.append(analysis)

    if os.path.exists(temp_path):
        os.remove(temp_path)

    return saved
