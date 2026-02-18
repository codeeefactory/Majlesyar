from datetime import timedelta
import re
import uuid

from django.utils import timezone
from rest_framework import serializers

from catalog.models import Product
from site_settings.models import SiteSetting

from .models import Order, OrderItem, OrderNote


class OrderNoteSerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = OrderNote
        fields = ("id", "note", "created_at", "created_by")


class OrderItemSerializer(serializers.ModelSerializer):
    product_id = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = (
            "id",
            "product_id",
            "name",
            "quantity",
            "price",
            "is_custom_pack",
            "custom_config",
        )

    def get_product_id(self, obj: OrderItem) -> str | None:
        return str(obj.product_id) if obj.product_id else None


class OrderSerializer(serializers.ModelSerializer):
    customer = serializers.SerializerMethodField()
    delivery = serializers.SerializerMethodField()
    items = OrderItemSerializer(many=True, read_only=True)
    notes = OrderNoteSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            "public_id",
            "status",
            "customer",
            "delivery",
            "payment_method",
            "total",
            "created_at",
            "items",
            "notes",
        )

    def get_customer(self, obj: Order) -> dict:
        return {
            "name": obj.customer_name,
            "phone": obj.customer_phone,
            "province": obj.customer_province,
            "address": obj.customer_address,
            "notes": obj.customer_notes or None,
        }

    def get_delivery(self, obj: Order) -> dict:
        return {
            "date": obj.delivery_date.isoformat(),
            "window": obj.delivery_window,
        }


class CustomerInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    phone = serializers.CharField(max_length=32)
    province = serializers.CharField(max_length=128)
    address = serializers.CharField()
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_phone(self, value: str) -> str:
        if not re.match(r"^09\d{9}$", value):
            raise serializers.ValidationError("Phone number must match Iranian mobile format.")
        return value


class DeliveryInputSerializer(serializers.Serializer):
    date = serializers.DateField()
    window = serializers.CharField(max_length=64)


class OrderItemInputSerializer(serializers.Serializer):
    product_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    name = serializers.CharField(max_length=255)
    quantity = serializers.IntegerField(min_value=1)
    price = serializers.IntegerField(min_value=0)
    is_custom_pack = serializers.BooleanField(required=False, default=False)
    custom_config = serializers.JSONField(required=False, allow_null=True)


class OrderCreateSerializer(serializers.Serializer):
    items = OrderItemInputSerializer(many=True, min_length=1)
    customer = CustomerInputSerializer()
    delivery = DeliveryInputSerializer()
    payment_method = serializers.CharField(max_length=64)

    def validate(self, attrs):
        settings = SiteSetting.load()
        items = attrs.get("items", [])
        customer = attrs["customer"]
        delivery = attrs["delivery"]
        payment_method = attrs["payment_method"]

        total_qty = sum(item["quantity"] for item in items)
        if total_qty < settings.min_order_qty:
            raise serializers.ValidationError(
                {"items": f"Minimum order quantity is {settings.min_order_qty}."}
            )

        if settings.allowed_provinces and customer["province"] not in settings.allowed_provinces:
            raise serializers.ValidationError({"customer": {"province": "Province is not allowed."}})

        enabled_payment_methods = {
            method.get("id")
            for method in settings.payment_methods
            if isinstance(method, dict) and method.get("enabled")
        }
        if enabled_payment_methods and payment_method not in enabled_payment_methods:
            raise serializers.ValidationError({"payment_method": "Payment method is not enabled."})

        min_delivery_date = (timezone.localtime() + timedelta(hours=settings.lead_time_hours)).date()
        if delivery["date"] < min_delivery_date:
            raise serializers.ValidationError(
                {"delivery": {"date": f"Delivery date must be on or after {min_delivery_date.isoformat()}."}}
            )

        return attrs

    def create(self, validated_data):
        customer = validated_data["customer"]
        delivery = validated_data["delivery"]

        order = Order.objects.create(
            customer_name=customer["name"],
            customer_phone=customer["phone"],
            customer_province=customer["province"],
            customer_address=customer["address"],
            customer_notes=customer.get("notes", ""),
            delivery_date=delivery["date"],
            delivery_window=delivery["window"],
            payment_method=validated_data["payment_method"],
            status=Order.Status.PENDING,
            total=0,
        )

        total = 0
        for item_data in validated_data["items"]:
            product = None
            raw_product_id = item_data.get("product_id")
            if raw_product_id:
                try:
                    product_uuid = uuid.UUID(str(raw_product_id))
                    product = Product.objects.filter(pk=product_uuid).first()
                except (ValueError, TypeError):
                    product = None

            line_total = item_data["quantity"] * item_data["price"]
            total += line_total

            OrderItem.objects.create(
                order=order,
                product=product,
                name=item_data["name"],
                quantity=item_data["quantity"],
                price=item_data["price"],
                is_custom_pack=item_data.get("is_custom_pack", False),
                custom_config=item_data.get("custom_config"),
            )

        order.total = total
        order.save(update_fields=["total", "updated_at"])
        return order


class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ("status",)


class OrderNoteCreateSerializer(serializers.Serializer):
    note = serializers.CharField()
