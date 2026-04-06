from django.apps import AppConfig


class CatalogConfig(AppConfig):
    name = 'catalog'
    verbose_name = "کاتالوگ"

    def ready(self) -> None:
        from .image_utils import register_image_plugins

        register_image_plugins()
