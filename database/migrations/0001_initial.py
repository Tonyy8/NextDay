from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ClothingAnalysis",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to="uploads/%Y/%m/%d/")),
                ("annotated_image", models.ImageField(blank=True, null=True, upload_to="results/%Y/%m/%d/")),
                ("class_name", models.CharField(max_length=100)),
                ("confidence", models.FloatField()),
                ("bbox_x1", models.IntegerField()),
                ("bbox_y1", models.IntegerField()),
                ("bbox_x2", models.IntegerField()),
                ("bbox_y2", models.IntegerField()),
                ("aspect_ratio", models.FloatField()),
                ("shape_label", models.CharField(max_length=50)),
                ("primary_color_hex", models.CharField(max_length=7)),
                ("primary_color_rgb", models.CharField(max_length=20)),
                ("dominant_colors", models.JSONField(default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "การวิเคราะห์เสื้อผ้า",
                "verbose_name_plural": "การวิเคราะห์เสื้อผ้า",
                "db_table": "clothing_analysis",
                "ordering": ["-created_at"],
            },
        ),
    ]
