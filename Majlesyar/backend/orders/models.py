from django.db import models
import uuid
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator

from catalog.models import Product


User = get_user_model()


def generate_order_public_id() -> str:
    return f"ORD-{uuid.uuid4().hex[:8].upper()}"


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        PREPARING = "preparing", "Preparing"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"

    public_id = models.CharField(max_length=20, unique=True, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    customer_name = models.CharField(max_length=255)
    customer_phone = models.CharField(max_length=32)
    customer_province = models.CharField(max_length=128)
    customer_address = models.TextField()
    customer_notes = models.TextField(blank=True)

    delivery_date = models.DateField()
    delivery_window = models.CharField(max_length=64)

    payment_method = models.CharField(max_length=64)
    total = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Order"
        verbose_name_plural = "Orders"

    def save(self, *args, **kwargs):
        if not self.public_id:
            while True:
                candidate = generate_order_public_id()
                if not Order.objects.filter(public_id=candidate).exists():
                    self.public_id = candidate
                    break
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.public_id


class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    price = models.PositiveIntegerField(validators=[MinValueValidator(0)])
    is_custom_pack = models.BooleanField(default=False)
    custom_config = models.JSONField(default=dict, blank=True, null=True)

    class Meta:
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"

    def __str__(self) -> str:
        return f"{self.name} x {self.quantity}"


class OrderNote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="notes")
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_notes",
    )

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Order Note"
        verbose_name_plural = "Order Notes"

    def __str__(self) -> str:
        return f"Note for {self.order.public_id}"

# Create your models here.
