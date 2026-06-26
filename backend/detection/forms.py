from django import forms


class ImageUploadForm(forms.Form):
    image = forms.ImageField(
        label="อัปโหลดรูปภาพเสื้อผ้า",
        help_text="รองรับไฟล์ JPG, PNG (สูงสุด 10 MB)",
        widget=forms.ClearableFileInput(attrs={"accept": "image/*", "class": "form-input"}),
    )

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image and image.size > 10 * 1024 * 1024:
            raise forms.ValidationError("ขนาดไฟล์ต้องไม่เกิน 10 MB")
        return image
