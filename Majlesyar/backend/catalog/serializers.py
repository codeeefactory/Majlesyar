from rest_framework import serializers

from .models import BuilderItem, Category, Product


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug", "icon")


class ProductSerializer(serializers.ModelSerializer):
    category_ids = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "description",
            "price",
            "category_ids",
            "event_types",
            "contents",
            "image",
            "featured",
            "available",
        )

    def get_category_ids(self, obj: Product) -> list[str]:
        return [str(category_id) for category_id in obj.categories.values_list("id", flat=True)]

    def get_image(self, obj: Product) -> str | None:
        if not obj.image:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url


class BuilderItemSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = BuilderItem
        fields = ("id", "name", "group", "price", "required", "image")

    def get_image(self, obj: BuilderItem) -> str | None:
        if not obj.image:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url
