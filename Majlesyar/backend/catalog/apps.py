from django.apps import AppConfig


class CatalogConfig(AppConfig):
    name = 'catalog'
    verbose_name = "کاتالوگ"

    def ready(self) -> None:
        from .image_utils import register_image_plugins
        from . import signals  # noqa: F401

        register_image_plugins()
