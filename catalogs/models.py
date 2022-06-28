import os

from django.db import models
from django.dispatch import receiver


class Catalog(models.Model):
    name = models.CharField(max_length=100, help_text="Name of Catalog", unique=True)
    file_name = models.FileField(
        max_length=100, help_text="Location of static catalog data file", unique=True
    )
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    updated = models.DateTimeField(auto_now=True, db_index=True, null=True)


@receiver(models.signals.post_delete, sender=Catalog)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """
    Delete files from the filesystem when a Catalog oject is deleted.
    """
    if instance.file_name:
        if os.path.isfile(instance.file_name.path):
            os.remove(instance.file_name.path)


@receiver(models.signals.pre_save, sender=Catalog)
def auto_delete_file_on_change(sender, instance, **kwargs):
    """
    Delete old file from filesystem when Catalog object is update with a new file.
    """
    if not instance.pk:
        return False

    try:
        old_file = Catalog.objects.get(pk=instance.pk).file_name
    except Catalog.DoesNotExist:
        return False

    new_file = instance.file
    if not old_file == new_file:
        if os.path.isfile(old_file.path):
            os.remove(old_file.path)