from django import forms

from database.models import FABRIC_THICKNESS_CHOICES, GARMENT_TYPES, ClothingItem

WARDROBE_COLORS = [
    ("#ffffff", "ขาว"),
    ("#f8fafc", "ขาวนวล"),
    ("#111827", "ดำ"),
    ("#6b7280", "เทา"),
    ("#faf3e8", "ครีม"),
    ("#d4b896", "เบจ"),
    ("#c4a574", "กากี"),
    ("#dc2626", "แดง"),
    ("#f97316", "ส้ม"),
    ("#eab308", "เหลือง"),
    ("#16a34a", "เขียว"),
    ("#38bdf8", "ฟ้า"),
    ("#2c5ead", "น้ำเงิน"),
    ("#1e3a5f", "กรม"),
    ("#7c3aed", "ม่วง"),
    ("#ec4899", "ชมพู"),
]

FORMALITY_CHOICES = [
    (1, "1 — สบายมาก"),
    (2, "2 — สบาย"),
    (3, "3 — ลำลอง"),
    (4, "4 — กึ่งทางการ"),
    (5, "5 — ทางการ"),
    (6, "6 — ทางการมาก"),
]

WARDROBE_COLOR_HEXES = {hex_code for hex_code, _ in WARDROBE_COLORS}


def snap_to_palette(hex_code: str) -> str:
    from wardrobe.services.color_utils import hex_to_rgb

    if not hex_code:
        return WARDROBE_COLORS[0][0]
    target = hex_code.lower()
    if target in WARDROBE_COLOR_HEXES:
        return target
    tr, tg, tb = hex_to_rgb(target)
    best = WARDROBE_COLORS[0][0]
    best_dist = float("inf")
    for h, _ in WARDROBE_COLORS:
        r, g, b = hex_to_rgb(h)
        dist = (tr - r) ** 2 + (tg - g) ** 2 + (tb - b) ** 2
        if dist < best_dist:
            best_dist = dist
            best = h
    return best


def color_label_for_hex(hex_code: str) -> str:
    hex_code = snap_to_palette(hex_code)
    return dict(WARDROBE_COLORS).get(hex_code, "ไม่ระบุ")


class ItemEditForm(forms.Form):
    garment_type = forms.ChoiceField(
        choices=GARMENT_TYPES,
        label="ประเภทเสื้อผ้า",
        widget=forms.Select(attrs={"class": "form-input"}),
    )
    part = forms.ChoiceField(
        choices=[("top", "ท่อนบน"), ("bottom", "ท่อนล่าง")],
        label="ท่อน",
        widget=forms.Select(attrs={"class": "form-input"}),
    )
    formality = forms.TypedChoiceField(
        choices=FORMALITY_CHOICES,
        coerce=int,
        label="ความเป็นทางการ",
        widget=forms.Select(attrs={"class": "form-input"}),
    )
    fabric_thickness = forms.ChoiceField(
        choices=FABRIC_THICKNESS_CHOICES,
        label="ความหนาผ้า",
        widget=forms.Select(attrs={"class": "form-input"}),
    )
    primary_color_hex = forms.CharField(widget=forms.HiddenInput())

    def clean_primary_color_hex(self):
        hex_code = self.cleaned_data["primary_color_hex"].lower()
        if hex_code not in WARDROBE_COLOR_HEXES:
            raise forms.ValidationError("กรุณาเลือกสีจากตัวเลือก")
        return hex_code


class WardrobeSearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        label="ค้นหา",
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "ค้นหาสี, ประเภท..."}),
    )
    garment_type = forms.ChoiceField(
        required=False,
        label="ประเภท",
        choices=[("", "ทั้งหมด")] + GARMENT_TYPES,
        widget=forms.Select(attrs={"class": "form-input"}),
    )


class SaveOutfitForm(forms.Form):
    name = forms.CharField(
        required=False,
        label="ชื่อชุด",
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "เช่น ชุดออฟฟิศสุดคูล"}),
    )


STYLE_PREF_CHOICES = [
    ("สบายๆ", "สบายๆ (Casual)"),
    ("สมาร์ทแคชชวล", "สมาร์ทแคชชวล (Smart Casual)"),
    ("ทางการ", "ทางการ (Formal)"),
    ("กีฬา", "กีฬา (Sporty)"),
]


class ProfileForm(forms.Form):
    display_name = forms.CharField(
        label="ชื่อที่แสดง",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "ชื่อของคุณ"}),
    )
    email = forms.EmailField(
        label="อีเมล",
        widget=forms.EmailInput(attrs={"class": "form-input", "placeholder": "you@example.com"}),
    )
    style_pref = forms.ChoiceField(
        label="สไตล์ที่ชอบ",
        choices=STYLE_PREF_CHOICES,
        widget=forms.Select(attrs={"class": "form-input"}),
    )
    weight_correctness = forms.IntegerField(
        label="ความถูกต้องตามโอกาส (%)",
        min_value=0,
        max_value=100,
        widget=forms.NumberInput(attrs={"class": "form-input", "min": 0, "max": 100}),
    )
    weight_weather = forms.IntegerField(
        label="เหมาะกับอากาศ (%)",
        min_value=0,
        max_value=100,
        widget=forms.NumberInput(attrs={"class": "form-input", "min": 0, "max": 100}),
    )
    weight_color = forms.IntegerField(
        label="ความเข้ากันของสี (%)",
        min_value=0,
        max_value=100,
        widget=forms.NumberInput(attrs={"class": "form-input", "min": 0, "max": 100}),
    )

    def clean(self):
        cleaned = super().clean()
        c = cleaned.get("weight_correctness")
        w = cleaned.get("weight_weather")
        col = cleaned.get("weight_color")
        if None not in (c, w, col) and (c + w + col) != 100:
            raise forms.ValidationError("น้ำหนักทั้ง 3 ส่วนต้องรวมกันได้ 100%")
        return cleaned
