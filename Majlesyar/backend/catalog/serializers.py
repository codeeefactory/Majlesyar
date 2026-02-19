from rest_framework import serializers
from PIL import Image, UnidentifiedImageError

from .models import BuilderItem, Category, Product


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug", "icon")


class ProductSerializer(serializers.ModelSerializer):
    category_ids = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    image_name = serializers.SerializerMethodField()

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
            "image_name",
            "image_alt",
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

    def get_image_name(self, obj: Product) -> str:
        if obj.image_name:
            return obj.image_name
        if obj.image:
            return str(obj.image.name).split("/")[-1]
        return ""


class ProductWriteSerializer(serializers.ModelSerializer):
    category_ids = serializers.ListField(
        child=serializers.UUIDField(format="hex_verbose"),
        required=False,
        allow_empty=True,
    )
    event_types = serializers.ListField(
        child=serializers.CharField(max_length=64, allow_blank=False),
        required=False,
        allow_empty=True,
    )
    contents = serializers.ListField(
        child=serializers.CharField(max_length=255, allow_blank=False),
        required=False,
        allow_empty=True,
    )
    # برای سازگاری با فرانت، مقدار image نیز پذیرفته می شود.
    image = serializers.CharField(required=False, allow_blank=True, allow_null=True, write_only=True)
    image_file = serializers.ImageField(required=False, allow_null=True, write_only=True)

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
            "image_file",
            "image_name",
            "image_alt",
            "featured",
            "available",
        )
        read_only_fields = ("id",)

    def validate_category_ids(self, value: list) -> list:
        if not value:
            return value
        requested_ids = [str(item) for item in value]
        found_ids = set(
            str(item) for item in Category.objects.filter(id__in=requested_ids).values_list("id", flat=True)
        )
        missing = [item for item in requested_ids if item not in found_ids]
        if missing:
            raise serializers.ValidationError(
                f"شناسه دسته بندی نامعتبر است: {', '.join(missing)}",
            )
        return value

    def validate_event_types(self, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]

    def validate_contents(self, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]

    def validate_image_name(self, value: str) -> str:
        return (value or "").strip()

    def validate_image_alt(self, value: str) -> str:
        return (value or "").strip()

    def validate_image_file(self, value):
        max_size_bytes = 5 * 1024 * 1024
        if value.size > max_size_bytes:
            raise serializers.ValidationError("حجم تصویر باید حداکثر ۵ مگابایت باشد.")

        try:
            image = Image.open(value)
            image.verify()
        except (UnidentifiedImageError, OSError):
            raise serializers.ValidationError("فایل بارگذاری شده تصویر معتبر نیست.") from None
        finally:
            value.seek(0)

        return value

    def create(self, validated_data: dict) -> Product:
        category_ids = validated_data.pop("category_ids", [])
        validated_data.pop("image", None)
        image_file = validated_data.pop("image_file", serializers.empty)
        if image_file is not serializers.empty:
            validated_data["image"] = image_file

        product = Product.objects.create(**validated_data)
        if category_ids is not None:
            product.categories.set(Category.objects.filter(id__in=category_ids))
        return product

    def update(self, instance: Product, validated_data: dict) -> Product:
        category_ids = validated_data.pop("category_ids", serializers.empty)
        image_marker = validated_data.pop("image", serializers.empty)
        image_file = validated_data.pop("image_file", serializers.empty)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if image_file is not serializers.empty:
            instance.image = image_file
        elif image_marker is None:
            instance.image.delete(save=False)
            instance.image = None
            instance.image_name = ""

        instance.save()

        if category_ids is not serializers.empty:
            instance.categories.set(Category.objects.filter(id__in=category_ids))

        return instance


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
