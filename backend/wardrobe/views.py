from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from database.models import ClothingItem, Destination, FavoriteOutfit, GARMENT_TYPES, FABRIC_THICKNESS_CHOICES
from wardrobe.forms import ItemEditForm, ProfileForm, SaveOutfitForm, WardrobeSearchForm, WARDROBE_COLORS, FORMALITY_CHOICES, snap_to_palette
from wardrobe.services import ClothingProcessor, OutfitBuilder
from wardrobe.services.color_utils import rgb_to_lab, thai_color_name
from wardrobe.services.destination_profiles import STYLE_LABELS, WEATHER_LABELS, build_matrix_a
from wardrobe import mock_data as mock


def _outfit_matrix_context(destination):
    matrix_a = build_matrix_a(destination)
    return {
        "matrix_weather": WEATHER_LABELS.get(matrix_a.weather, matrix_a.weather),
        "matrix_style": STYLE_LABELS.get(matrix_a.style, matrix_a.style),
    }


@login_required
def dashboard(request):
    if settings.MOCK_MODE:
        return render(request, "wardrobe/dashboard.html", mock.dashboard_context(request))

    items = ClothingItem.objects.filter(user=request.user)
    item_list = list(items)
    favorites_qs = FavoriteOutfit.objects.filter(user=request.user).select_related(
        "destination", "top_item", "bottom_item"
    )
    destinations = Destination.objects.all()

    dest_stats = []
    for dest in destinations:
        allowed = set(dest.allowed_categories)
        count = sum(1 for i in item_list if i.garment_type in allowed)
        dest_stats.append({"dest": dest, "count": count})

    color_map = {}
    for item in item_list:
        if item.primary_color_hex not in color_map:
            color_map[item.primary_color_hex] = item.color_name_th or item.primary_color_hex

    unique_colors = [{"hex": h, "name": n} for h, n in list(color_map.items())[:8]]
    avg_formality = sum(i.formality for i in item_list) / len(item_list) if item_list else 0
    diversity = min(100, len(color_map) * 12) if item_list else 0
    latest_fav = favorites_qs.first()
    match_score = latest_fav.match_score if latest_fav else 0

    username = request.user.username.split("@")[0]
    avatar_letter = (username[:1] or "U").upper()

    return render(request, "wardrobe/dashboard.html", {
        "total": len(item_list),
        "needs_review": sum(1 for i in item_list if i.needs_review),
        "favorites_count": favorites_qs.count(),
        "suggest_today": min(3, favorites_qs.count()) if favorites_qs.exists() else 0,
        "recent": item_list[:3],
        "destinations": dest_stats,
        "unique_colors": unique_colors,
        "latest_fav": latest_fav,
        "match_score": round(match_score),
        "diversity": round(diversity),
        "formality_pct": round(avg_formality / 6 * 100) if item_list else 0,
        "unused_count": sum(1 for i in item_list if not i.is_verified),
        "username": username,
        "avatar_letter": avatar_letter,
    })


@login_required
@require_http_methods(["GET", "POST"])
def upload(request):
    if settings.MOCK_MODE:
        if request.method == "POST":
            files = request.FILES.getlist("images")
            if not files:
                messages.error(request, "กรุณาเลือกรูปภาพ")
                return redirect("wardrobe:upload")
            created = mock.add_uploaded_items(request, files)
            if not created:
                messages.error(request, "ไม่สามารถอ่านไฟล์รูปได้ ลองใหม่อีกครั้ง")
                return redirect("wardrobe:upload")
            request.session["mock_last_upload"] = [rec["pk"] for rec in created]
            request.session.modified = True
            return redirect("wardrobe:upload_result")
        return render(request, "wardrobe/upload.html")

    if request.method == "POST":
        files = request.FILES.getlist("images")
        if not files:
            messages.error(request, "กรุณาเลือกรูปภาพ")
            return redirect("wardrobe:upload")

        processor = ClothingProcessor()
        created = []
        for f in files:
            try:
                item = processor.process_upload(request.user, f)
                created.append(item)
            except Exception as exc:
                messages.warning(request, f"ไม่สามารถประมวลผล {f.name}: {exc}")

        review_count = sum(1 for i in created if i.needs_review)
        messages.success(request, f"อัปโหลดสำเร็จ {len(created)} ชิ้น" + (f" ({review_count} ชิ้นต้องตรวจสอบ)" if review_count else ""))
        return redirect("wardrobe:wardrobe")

    return render(request, "wardrobe/upload.html")


@login_required
def upload_result(request):
    if not settings.MOCK_MODE:
        return redirect("wardrobe:wardrobe")
    pks = request.session.get("mock_last_upload", [])
    items = mock.get_items_by_pks(request, pks)
    if not items:
        return redirect("wardrobe:upload")
    return render(request, "wardrobe/upload_result.html", {"items": items})


@login_required
def wardrobe_list(request):
    if settings.MOCK_MODE:
        return render(request, "wardrobe/wardrobe.html", mock.wardrobe_context(request))

    form = WardrobeSearchForm(request.GET or None)
    items = ClothingItem.objects.filter(user=request.user)

    if form.is_valid():
        q = form.cleaned_data.get("q")
        gt = form.cleaned_data.get("garment_type")
        if q:
            items = items.filter(
                Q(color_name_th__icontains=q) | Q(garment_type__icontains=q)
            )
        if gt:
            items = items.filter(garment_type=gt)

    return render(request, "wardrobe/wardrobe.html", {
        "items": items,
        "total_items": ClothingItem.objects.filter(user=request.user).count(),
        "form": form,
        "garment_types": GARMENT_TYPES,
        "color_choices": WARDROBE_COLORS,
        "formality_choices": FORMALITY_CHOICES,
        "thickness_choices": FABRIC_THICKNESS_CHOICES,
    })


@login_required
@require_http_methods(["GET", "POST"])
def wardrobe_edit(request, pk):
    if settings.MOCK_MODE:
        ctx = mock.item_edit_context(pk, request)
        item = ctx.get("item")
        if not item:
            messages.error(request, "ไม่พบเสื้อผ้านี้")
            return redirect("wardrobe:wardrobe")
        if request.method == "POST":
            form = ItemEditForm(request.POST)
            if form.is_valid():
                mock.save_item_edit(request, pk, form.cleaned_data)
                messages.success(request, "อัปเดตเสื้อผ้าแล้ว")
                return redirect("wardrobe:wardrobe")
        else:
            form = ItemEditForm(initial=ctx["edit_initial"])
        return render(request, "wardrobe/wardrobe_edit.html", {
            "form": form,
            "item": item,
            "color_choices": WARDROBE_COLORS,
            "formality_choices": FORMALITY_CHOICES,
            "selected_color": snap_to_palette(item.primary_color_hex),
        })

    item = get_object_or_404(ClothingItem, pk=pk, user=request.user)
    if request.method == "POST":
        form = ItemEditForm(request.POST)
        if form.is_valid():
            _apply_item_edit(item, form.cleaned_data)
            item.is_verified = True
            item.needs_review = False
            item.save()
            messages.success(request, "อัปเดตเสื้อผ้าแล้ว")
            return redirect("wardrobe:wardrobe")
    else:
        form = ItemEditForm(initial={
            "garment_type": item.garment_type,
            "part": item.part,
            "formality": item.formality,
            "fabric_thickness": item.fabric_thickness,
            "primary_color_hex": snap_to_palette(item.primary_color_hex),
        })

    return render(request, "wardrobe/wardrobe_edit.html", {
        "form": form,
        "item": item,
        "color_choices": WARDROBE_COLORS,
        "formality_choices": FORMALITY_CHOICES,
        "selected_color": snap_to_palette(item.primary_color_hex),
    })


def _apply_item_edit(item, data):
    item.garment_type = data["garment_type"]
    item.part = data["part"]
    item.formality = data["formality"]
    item.fabric_thickness = data["fabric_thickness"]
    item.primary_color_hex = data["primary_color_hex"]
    item.color_name_th = thai_color_name(data["primary_color_hex"])
    r, g, b = int(item.primary_color_hex[1:3], 16), int(item.primary_color_hex[3:5], 16), int(item.primary_color_hex[5:7], 16)
    item.lab_l, item.lab_a, item.lab_b = rgb_to_lab(r, g, b)


@login_required
@require_POST
def wardrobe_delete(request, pk):
    if settings.MOCK_MODE:
        messages.info(request, "ลบเสื้อผ้าแล้ว (Mockup)")
        return redirect("wardrobe:wardrobe")

    item = get_object_or_404(ClothingItem, pk=pk, user=request.user)
    item.delete()
    messages.info(request, "ลบเสื้อผ้าออกจากตู้แล้ว (ไฟล์ภาพถูกลบจากเซิร์ฟเวอร์ด้วย)")
    return redirect("wardrobe:wardrobe")


@login_required
@require_http_methods(["GET", "POST"])
def verify(request, pk):
    if settings.MOCK_MODE:
        ctx = mock.verify_context(pk, request)
        item = ctx["item"]
        if request.method == "POST":
            form = ItemEditForm(request.POST)
            if form.is_valid():
                mock.save_item_edit(request, pk, form.cleaned_data)
                messages.success(request, "ยืนยันข้อมูลเรียบร้อย")
                return redirect("wardrobe:wardrobe")
        else:
            form = ItemEditForm(initial=ctx["edit_initial"])
        return render(request, "wardrobe/verify.html", {
            "form": form,
            "item": item,
            "color_choices": WARDROBE_COLORS,
            "formality_choices": FORMALITY_CHOICES,
            "selected_color": snap_to_palette(item.primary_color_hex),
        })

    item = get_object_or_404(ClothingItem, pk=pk, user=request.user)
    if request.method == "POST":
        form = ItemEditForm(request.POST)
        if form.is_valid():
            _apply_item_edit(item, form.cleaned_data)
            item.is_verified = True
            item.needs_review = False
            item.save()
            messages.success(request, "ยืนยันข้อมูลเรียบร้อย")
            return redirect("wardrobe:wardrobe")
    else:
        form = ItemEditForm(initial={
            "garment_type": item.garment_type,
            "part": item.part,
            "formality": item.formality,
            "fabric_thickness": item.fabric_thickness,
            "primary_color_hex": snap_to_palette(item.primary_color_hex),
        })

    return render(request, "wardrobe/verify.html", {
        "form": form,
        "item": item,
        "color_choices": WARDROBE_COLORS,
        "formality_choices": FORMALITY_CHOICES,
        "selected_color": snap_to_palette(item.primary_color_hex),
    })


@login_required
def outfit_builder(request):
    if settings.MOCK_MODE:
        return render(request, "wardrobe/outfit.html", mock.outfit_context(request))

    destinations = Destination.objects.all()
    builder = OutfitBuilder()
    dest_id = request.GET.get("destination")
    swap_slot = request.GET.get("swap")
    swap_piece = request.GET.get("piece")

    context = {
        "destinations": destinations,
        "step": 1,
        "swap_slot": swap_slot,
        "swap_piece": swap_piece,
    }

    if dest_id:
        destination = get_object_or_404(Destination, pk=dest_id)
        user_items = list(ClothingItem.objects.filter(user=request.user))
        overrides = _parse_slot_overrides(request)
        outfits = builder.suggest_outfits(user_items, destination, slot_overrides=overrides)
        outfit_base_url = _enrich_outfit_urls(destination, outfits, overrides)
        context.update({
            "step": 2,
            "destination": destination,
            "outfits": outfits,
            "slot_overrides": overrides,
            "outfit_base_url": outfit_base_url,
            **_outfit_matrix_context(destination),
        })

        if swap_slot is not None and swap_piece in ("top", "bottom"):
            slot_idx = int(swap_slot)
            if slot_idx < len(outfits):
                current = outfits[slot_idx]
                ref_item = current.top if swap_piece == "top" else current.bottom
                alts = builder.part_alternatives(ref_item, user_items, destination)
                context["swap_alternatives"] = [
                    {
                        "item": alt,
                        "url": _build_outfit_query(destination, slot_idx, swap_piece, alt.pk, overrides),
                    }
                    for alt in alts[:6]
                ]
                context["swap_current"] = ref_item

    return render(request, "wardrobe/outfit.html", context)


def _parse_slot_overrides(request, count=3):
    overrides = {}
    for i in range(count):
        top = request.GET.get(f"t{i}")
        bottom = request.GET.get(f"b{i}")
        if top or bottom:
            overrides[i] = {}
            if top:
                overrides[i]["top"] = int(top)
            if bottom:
                overrides[i]["bottom"] = int(bottom)
    return overrides


def _build_outfit_query(destination, slot_idx, piece, item_pk, overrides):
    params = [f"destination={destination.pk}"]
    slots = {i: dict(overrides.get(i, {})) for i in range(3)}
    if piece == "top":
        slots[slot_idx]["top"] = item_pk
    else:
        slots[slot_idx]["bottom"] = item_pk
    for i in range(3):
        if "top" in slots[i]:
            params.append(f"t{i}={slots[i]['top']}")
        if "bottom" in slots[i]:
            params.append(f"b{i}={slots[i]['bottom']}")
    return "?" + "&".join(params)


def _outfit_base_query(destination, outfits, overrides):
    params = [f"destination={destination.pk}"]
    for i, outfit in enumerate(outfits):
        top_pk = overrides.get(i, {}).get("top", outfit.top.pk)
        bottom_pk = overrides.get(i, {}).get("bottom", outfit.bottom.pk)
        params.append(f"t{i}={top_pk}")
        params.append(f"b{i}={bottom_pk}")
    return "&".join(params)


def _enrich_outfit_urls(destination, outfits, overrides):
    for i, outfit in enumerate(outfits):
        outfit.swap_top_url = f"?{_outfit_base_query(destination, outfits, overrides)}&swap={i}&piece=top"
        outfit.swap_bottom_url = f"?{_outfit_base_query(destination, outfits, overrides)}&swap={i}&piece=bottom"
    return f"?{_outfit_base_query(destination, outfits, overrides)}"


@login_required
@require_POST
def save_outfit(request):
    if settings.MOCK_MODE:
        messages.success(request, "บันทึกชุดโปรดเรียบร้อย (Mockup)")
        return redirect("wardrobe:favorites")

    top_id = request.POST.get("top_id")
    bottom_id = request.POST.get("bottom_id")
    dest_id = request.POST.get("destination_id")
    form = SaveOutfitForm(request.POST)

    top = get_object_or_404(ClothingItem, pk=top_id, user=request.user)
    bottom = get_object_or_404(ClothingItem, pk=bottom_id, user=request.user)
    destination = get_object_or_404(Destination, pk=dest_id) if dest_id else None

    from wardrobe.services import ColorMatcher
    match = ColorMatcher().score_pair(top, bottom)

    fav = FavoriteOutfit.objects.create(
        user=request.user,
        destination=destination,
        top_item=top,
        bottom_item=bottom,
        name=form.data.get("name", ""),
        match_score=match.score,
        match_theory=match.theory,
    )
    messages.success(request, f"บันทึกชุดโปรด #{fav.pk} เรียบร้อย")
    return redirect("wardrobe:favorites")


@login_required
def favorites(request):
    if settings.MOCK_MODE:
        return render(request, "wardrobe/favorites.html", mock.favorites_context())

    outfits = FavoriteOutfit.objects.filter(user=request.user).select_related(
        "destination", "top_item", "bottom_item"
    )
    return render(request, "wardrobe/favorites.html", {"outfits": outfits})


@login_required
@require_POST
def delete_favorite(request, pk):
    if settings.MOCK_MODE:
        messages.info(request, "ลบชุดโปรดแล้ว (Mockup)")
        return redirect("wardrobe:favorites")

    fav = get_object_or_404(FavoriteOutfit, pk=pk, user=request.user)
    fav.delete()
    messages.info(request, "ลบชุดโปรดแล้ว")
    return redirect("wardrobe:favorites")


def community(request):
    if settings.MOCK_MODE:
        return render(request, "wardrobe/community.html", mock.community_context())

    username = request.user.username.split("@")[0]
    return render(request, "wardrobe/community.html", {
        "posts": [],
        "username": username,
        "avatar_letter": (username[:1] or "U").upper(),
    })


@login_required
def manual_outfit(request):
    if settings.MOCK_MODE:
        return render(request, "wardrobe/manual_outfit.html", mock.manual_outfit_context(request))

    items = list(ClothingItem.objects.filter(user=request.user))
    tops = [i for i in items if i.part == "top"]
    bottoms = [i for i in items if i.part == "bottom"]
    return render(request, "wardrobe/manual_outfit.html", {
        "tops": tops,
        "bottoms": bottoms,
        "destinations": Destination.objects.all(),
    })


@login_required
@require_http_methods(["GET", "POST"])
def profile(request):
    if settings.MOCK_MODE:
        ctx = mock.profile_context(request)
        if request.method == "POST":
            form = ProfileForm(request.POST)
            if form.is_valid():
                mock.save_profile(request, form.cleaned_data)
                messages.success(request, "บันทึกโปรไฟล์เรียบร้อย")
                return redirect("wardrobe:profile")
        else:
            form = ProfileForm(initial=ctx["profile_initial"])
        ctx["form"] = form
        return render(request, "wardrobe/profile.html", ctx)

    items = ClothingItem.objects.filter(user=request.user)
    initial = {
        "display_name": request.user.get_full_name() or request.user.username,
        "email": request.user.email,
        "style_pref": request.session.get("style_pref", "สมาร์ทแคชชวล"),
        "weight_correctness": request.session.get("weight_correctness", 40),
        "weight_weather": request.session.get("weight_weather", 20),
        "weight_color": request.session.get("weight_color", 40),
    }
    if request.method == "POST":
        form = ProfileForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            request.user.first_name = data["display_name"]
            request.user.email = data["email"]
            request.user.save(update_fields=["first_name", "email"])
            request.session["style_pref"] = data["style_pref"]
            request.session["weight_correctness"] = data["weight_correctness"]
            request.session["weight_weather"] = data["weight_weather"]
            request.session["weight_color"] = data["weight_color"]
            messages.success(request, "บันทึกโปรไฟล์เรียบร้อย")
            return redirect("wardrobe:profile")
    else:
        form = ProfileForm(initial=initial)

    return render(request, "wardrobe/profile.html", {
        "form": form,
        "username": initial["display_name"],
        "email": initial["email"],
        "total_items": items.count(),
        "favorites_count": FavoriteOutfit.objects.filter(user=request.user).count(),
        "style_pref": initial["style_pref"],
        "weight_correctness": initial["weight_correctness"],
        "weight_weather": initial["weight_weather"],
        "weight_color": initial["weight_color"],
    })


@login_required
@require_http_methods(["GET", "POST"])
def feedback(request):
    if request.method == "POST":
        messages.success(request, "ส่งข้อเสนอแนะเรียบร้อย ขอบคุณที่ช่วยพัฒนา NEXTDAY")
        return redirect("wardrobe:feedback")
    return render(request, "wardrobe/feedback.html", {})
