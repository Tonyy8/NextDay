import os

from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from .models import ClothingItem


def _delete_file(field):
    if field and os.path.isfile(field.path):
        os.remove(field.path)


@receiver(post_delete, sender=ClothingItem)
def cleanup_clothing_files(sender, instance, **kwargs):
    _delete_file(instance.image)
    _delete_file(instance.cropped_image)


@receiver(pre_save, sender=ClothingItem)
def cleanup_replaced_files(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old = ClothingItem.objects.get(pk=instance.pk)
    except ClothingItem.DoesNotExist:
        return
    if old.image != instance.image:
        _delete_file(old.image)
    if old.cropped_image != instance.cropped_image:
        _delete_file(old.cropped_image)
