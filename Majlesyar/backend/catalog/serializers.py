import json
import os

from rest_framework import serializers
from PIL import Image, UnidentifiedImageError
from django.utils.text import slugify

from .image_utils import derive_image_label, image_extension_validator, image_supports_extension
from .image_variants import build_product_image_payload
from .models import (
    BuilderItem,
    Category,
    CustomerReview,
    PageProductPlacement,
    Product,
    Tag,
    PRODUCT_INPUT_MODE_NORMAL,
    PRODUCT_INPUT_MODE_PHOTO_PROCESSING,
    get_content_item_name,
    get_content_item_price,
    normalize_product_contents,
    sync_product_categories,
)
from .services import serialize_page_preview_target


def _parse_content_item(item):
    if isinstance(item, str) and item.strip().startswith("{"):
        try:
            parsed = json.loads(item)
        except json.JSONDecodeError:
            return item
        if isinstance(parsed, dict):
            return parsed
    return item


class CategorySerializer(serializers.ModelSerializer):
    logo = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ("id", "name", "slug", "icon", "color", "logo")

    def get_logo(self, obj: Category) -> str | None:
        if not obj.logo:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.logo.url)
        return obj.logo.url


class CategoryWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug", "icon", "color", "logo")
        read_only_fields = ("id",)

    def validate_slug(self, value: str) -> str:
        return slugify((value or "").strip())


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ("id", "name", "slug")


class TagWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ("id", "name", "slug")
        read_only_fields = ("id",)

    def validate_slug(self, value: str) -> str:
        return slugify((value or "").strip())


class CustomerReviewSerializer(serializers.ModelSerializer):
    product_id = serializers.SerializerMethodField()
    product_name = serializers.SerializerMethodField()

    class Meta:
        model = CustomerReview
        fields = (
            "id",
            "product_id",
            "product_name",
            "customer_name",
            "customer_city",
            "title",
            "comment",
            "rating",
            "is_featured",
            "display_order",
            "created_at",
        )

    def get_product_id(self, obj: CustomerReview) -> str | None:
        return str(obj.product_id) if obj.product_id else None

    def get_product_name(self, obj: CustomerReview) -> str | None:
        return obj.product.name if obj.product else None


class CustomerReviewWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerReview
        fields = (
            "id",
            "product",
            "customer_name",
            "customer_city",
            "title",
            "comment",
            "rating",
            "is_approved",
            "is_featured",
            "display_order",
        )
        read_only_fields = ("id",)

    def validate_customer_name(self, value: str) -> str:
        return (value or "").strip()

    def validate_customer_city(self, value: str) -> str:
        return (value or "").strip()

    def validate_title(self, value: str) -> str:
        return (value or "").strip()

    def validate_comment(self, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise serializers.ValidationError("متن نظر الزامی است.")
        return cleaned


class ProductSerializer(serializers.ModelSerializer):
    category_ids = serializers.SerializerMethodField()
    tag_ids = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    image_responsive = serializers.SerializerMethodField()
    image_name = serializers.SerializerMethodField()
    image_alt = serializers.SerializerMethodField()
    uri = serializers.SerializerMethodField()
    contents = serializers.SerializerMethodField()
    customer_reviews = serializers.SerializerMethodField()
    photo_analysis = serializers.JSONField(read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "url_slug",
            "uri",
            "description",
            "price",
            "category_ids",
            "tag_ids",
            "event_types",
            "contents",
            "customer_reviews",
            "image",
            "image_responsive",
            "image_name",
            "image_alt",
            "photo_analysis",
            "featured",
            "available",
        )

    def get_category_ids(self, obj: Product) -> list[str]:
        return [str(category_id) for category_id in obj.categories.values_list("id", flat=True)]

    def get_tag_ids(self, obj: Product) -> list[str]:
        return [str(tag_id) for tag_id in obj.tags.values_list("id", flat=True)]

    def get_image(self, obj: Product) -> str | None:
        if not obj.image:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url

    def get_image_responsive(self, obj: Product) -> dict:
        return build_product_image_payload(obj, request=self.context.get("request"))

    def get_image_name(self, obj: Product) -> str:
        if obj.image_name:
            return obj.image_name
        if obj.image:
            return derive_image_label(obj.image.name)
        return ""

    def get_image_alt(self, obj: Product) -> str:
        if obj.image_alt:
            return obj.image_alt
        if obj.image:
            return derive_image_label(obj.image.name)
        return ""

    def get_uri(self, obj: Product) -> str:
        return f"/product/{obj.url_slug}"

    def get_contents(self, obj: Product) -> list[dict]:
        return normalize_product_contents(obj.contents)

    def get_customer_reviews(self, obj: Product) -> list[dict]:
        reviews = obj.customer_reviews.filter(is_approved=True).order_by("display_order", "-is_featured", "-created_at")[:6]
        return CustomerReviewSerializer(reviews, many=True, context=self.context).data


class ProductWriteSerializer(serializers.ModelSerializer):
    input_mode = serializers.ChoiceField(
        choices=[PRODUCT_INPUT_MODE_NORMAL, PRODUCT_INPUT_MODE_PHOTO_PROCESSING],
        required=False,
        default=PRODUCT_INPUT_MODE_NORMAL,
        write_only=True,
    )
    category_ids = serializers.ListField(
        child=serializers.UUIDField(format="hex_verbose"),
        required=False,
        allow_empty=True,
    )
    tag_ids = serializers.ListField(
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
        child=serializers.JSONField(),
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
            "url_slug",
            "description",
            "price",
            "input_mode",
            "category_ids",
            "tag_ids",
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

    def validate_contents(self, value: list) -> list[dict]:
        parsed_value = [_parse_content_item(item) for item in value]
        for item in parsed_value:
            name = get_content_item_name(item)
            if not name:
                raise serializers.ValidationError("Each pack content item needs a name.")
            if isinstance(item, dict):
                raw_price = item.get("price")
                if raw_price not in (None, "") and get_content_item_price(item) is None:
                    raise serializers.ValidationError("Each pack content price must be a non-negative number.")
        return normalize_product_contents(parsed_value)

    def validate_tag_ids(self, value: list) -> list:
        if not value:
            return value
        requested_ids = [str(item) for item in value]
        found_ids = set(
            str(item) for item in Tag.objects.filter(id__in=requested_ids).values_list("id", flat=True)
        )
        missing = [item for item in requested_ids if item not in found_ids]
        if missing:
            raise serializers.ValidationError(
                f"شناسه تگ نامعتبر است: {', '.join(missing)}",
            )
        return value

    def validate_image_name(self, value: str) -> str:
        return (value or "").strip()

    def validate_image_alt(self, value: str) -> str:
        return (value or "").strip()

    def validate_url_slug(self, value: str) -> str:
        cleaned = slugify((value or "").strip())
        if not cleaned:
            return ""
        return cleaned

    def validate_image_file(self, value):
        max_size_bytes = 5 * 1024 * 1024
        if value.size > max_size_bytes:
            raise serializers.ValidationError("حجم تصویر باید حداکثر ۵ مگابایت باشد.")

        image_extension_validator(value)
        _stem, extension = os.path.splitext(value.name or "")
        if extension and not image_supports_extension(value.name, extension):
            raise serializers.ValidationError("پشتیبانی AVIF نیازمند نصب بسته pillow-avif-plugin است.")

        try:
            image = Image.open(value)
            image.verify()
        except (UnidentifiedImageError, OSError):
            raise serializers.ValidationError("فایل بارگذاری شده تصویر معتبر نیست.") from None
        finally:
            value.seek(0)

        return value

    def create(self, validated_data: dict) -> Product:
        input_mode = validated_data.pop("input_mode", PRODUCT_INPUT_MODE_NORMAL)
        category_ids = validated_data.pop("category_ids", serializers.empty)
        tag_ids = validated_data.pop("tag_ids", [])
        validated_data.pop("image", None)
        image_file = validated_data.pop("image_file", serializers.empty)
        if image_file is not serializers.empty:
            validated_data["image"] = image_file
            if not validated_data.get("image_name"):
                validated_data["image_name"] = derive_image_label(image_file.name)
            if not validated_data.get("image_alt"):
                validated_data["image_alt"] = derive_image_label(image_file.name)

        product = Product(**validated_data)
        product._input_mode = input_mode
        product.save()
        if category_ids is not serializers.empty:
            product.categories.set(Category.objects.filter(id__in=category_ids))
        else:
            event_slugs = [slug for slug in (product.event_types or []) if isinstance(slug, str)]
            if event_slugs:
                product.categories.set(Category.objects.filter(slug__in=event_slugs))
        if tag_ids is not None:
            product.tags.set(Tag.objects.filter(id__in=tag_ids))
        sync_product_categories(product)
        return product

    def update(self, instance: Product, validated_data: dict) -> Product:
        input_mode = validated_data.pop("input_mode", PRODUCT_INPUT_MODE_NORMAL)
        category_ids = validated_data.pop("category_ids", serializers.empty)
        tag_ids = validated_data.pop("tag_ids", serializers.empty)
        image_marker = validated_data.pop("image", serializers.empty)
        image_file = validated_data.pop("image_file", serializers.empty)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if image_file is not serializers.empty:
            instance.image = image_file
            if not validated_data.get("image_name"):
                instance.image_name = derive_image_label(image_file.name)
            if not validated_data.get("image_alt"):
                instance.image_alt = derive_image_label(image_file.name)
        elif image_marker is None:
            instance.image.delete(save=False)
            instance.image = None
            instance.image_name = ""
            instance.image_alt = ""

        instance._input_mode = input_mode
        instance.save()

        if category_ids is not serializers.empty:
            instance.categories.set(Category.objects.filter(id__in=category_ids))
        elif not instance.categories.exists():
            event_slugs = [slug for slug in (instance.event_types or []) if isinstance(slug, str)]
            if event_slugs:
                instance.categories.set(Category.objects.filter(slug__in=event_slugs))
        if tag_ids is not serializers.empty:
            instance.tags.set(Tag.objects.filter(id__in=tag_ids))
        sync_product_categories(instance)

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


class BuilderItemWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = BuilderItem
        fields = ("id", "name", "group", "price", "required", "image")
        read_only_fields = ("id",)


class PagePreviewTargetSerializer(serializers.Serializer):
    page_type = serializers.CharField()
    page_slug = serializers.CharField(allow_blank=True)
    page_key = serializers.CharField()
    page_title = serializers.CharField()
    page_description = serializers.CharField(allow_blank=True)
    route_path = serializers.CharField()

    def to_representation(self, instance):
        if hasattr(instance, "page_key"):
            return serialize_page_preview_target(instance)
        return super().to_representation(instance)


class PageProductPlacementSerializer(serializers.ModelSerializer):
    page_key = serializers.SerializerMethodField()
    product_id = serializers.UUIDField(read_only=True)
    product = ProductSerializer(read_only=True)

    class Meta:
        model = PageProductPlacement
        fields = (
            "id",
            "page_type",
            "page_slug",
            "page_key",
            "position",
            "product_id",
            "product",
        )

    def get_page_key(self, obj: PageProductPlacement) -> str:
        if obj.page_type == PageProductPlacement.PageType.EVENT:
            return f"event:{obj.page_slug}"
        return obj.page_type


class PageProductPreviewSerializer(serializers.Serializer):
    page_type = serializers.CharField()
    page_slug = serializers.CharField(allow_blank=True)
    page_key = serializers.CharField()
    page_title = serializers.CharField()
    page_description = serializers.CharField(allow_blank=True)
    route_path = serializers.CharField()
    uses_custom_order = serializers.BooleanField()
    products = ProductSerializer(many=True)


class PageProductPlacementStateSerializer(serializers.Serializer):
    page_type = serializers.CharField()
    page_slug = serializers.CharField(allow_blank=True)
    page_key = serializers.CharField()
    page_title = serializers.CharField()
    page_description = serializers.CharField(allow_blank=True)
    route_path = serializers.CharField()
    uses_custom_order = serializers.BooleanField()
    placements = PageProductPlacementSerializer(many=True)
    preview_products = ProductSerializer(many=True)


class PageProductReorderSerializer(serializers.Serializer):
    page_type = serializers.ChoiceField(choices=PageProductPlacement.PageType.choices)
    page_slug = serializers.CharField(required=False, allow_blank=True)
    product_ids = serializers.ListField(
        child=serializers.UUIDField(format="hex_verbose"),
        allow_empty=True,
    )

    def validate(self, attrs):
        page_type = attrs.get("page_type")
        page_slug = (attrs.get("page_slug") or "").strip()
        if page_type == PageProductPlacement.PageType.EVENT and not page_slug:
            raise serializers.ValidationError({"page_slug": "برای صفحه رویداد باید اسلاگ رویداد مشخص شود."})
        attrs["page_slug"] = page_slug
        return attrs
