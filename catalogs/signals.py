import os

from catalogs.models import Catalog, Controls
from ratoapi.oscal.catalog import CatalogModel


# noinspection PyUnusedLocal
def add_controls(
    sender, instance: Catalog, created: bool, **kwargs
):  # pylint: disable=unused-argument
    if created:
        catalog_data = CatalogModel.from_json(instance.file_name.path)
        Controls.objects.bulk_create(
            [
                Controls(**{"catalog": instance, **item.to_orm()})
                for item in catalog_data.controls
            ]
        )


# noinspection PyUnusedLocal
def auto_delete_file_on_delete(
    sender, instance: Catalog, **kwargs
):  # pylint: disable=unused-argument
    """Delete files from the filesystem when a Catalog object is deleted."""
    if instance.file_name:
        if os.path.isfile(instance.file_name.path):
            os.remove(instance.file_name.path)


# noinspection PyUnusedLocal
def auto_delete_file_on_change(
    sender, instance: Catalog, **kwargs
):  # pylint: disable=unused-argument
    """Delete old file from filesystem when Catalog object is update with a new file."""
    if not instance.pk:
        return False

    try:
        old_file = Catalog.objects.get(pk=instance.pk).file_name
    except Catalog.DoesNotExist:
        return False

    new_file = instance.file_name
    if not old_file == new_file:
        if os.path.isfile(old_file.path):
            os.remove(old_file.path)
