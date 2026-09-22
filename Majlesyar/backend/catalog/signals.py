from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Product, ProductGalleryImage


@receiver(post_delete, sender=Product, dispatch_uid="catalog.delete_product_images_after_commit")
def schedule_deleted_product_image_cleanup(sender, instance: Product, using: str, **kwargs) -> None:
    from .media_cleanup import cleanup_deleted_product_images

    transaction.on_commit(
        lambda: cleanup_deleted_product_images(instance, using=using),
        using=using,
        robust=True,
    )


@receiver(
    post_delete,
    sender=ProductGalleryImage,
    dispatch_uid="catalog.delete_product_gallery_image_after_commit",
)
def schedule_deleted_product_gallery_image_cleanup(
    sender,
    instance: ProductGalleryImage,
    using: str,
    **kwargs,
) -> None:
    if not instance.image:
        return

    from .media_cleanup import cleanup_product_gallery_image

    image_name = instance.image.name
    transaction.on_commit(
        lambda: cleanup_product_gallery_image(image_name),
        using=using,
        robust=True,
    )
