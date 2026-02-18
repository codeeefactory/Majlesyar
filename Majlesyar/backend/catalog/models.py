import uuid

from django.core.validators import MinValueValidator
from django.db import models


class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=128)
    slug = models.SlugField(max_length=128, unique=True)
    icon = models.CharField(max_length=32, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self) -> str:
        return self.name


class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Price in Tomans. Leave empty for call-for-price products.",
    )
    categories = models.ManyToManyField(Category, related_name="products", blank=True)
    event_types = models.JSONField(default=list, blank=True)
    contents = models.JSONField(default=list, blank=True)
    image = models.ImageField(upload_to="products/", blank=True, null=True)
    featured = models.BooleanField(default=False)
    available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-featured", "name"]
        verbose_name = "Product"
        verbose_name_plural = "Products"

    def __str__(self) -> str:
        return self.name


class BuilderItem(models.Model):
    class Group(models.TextChoices):
        PACKAGING = "packaging", "Packaging"
        FRUIT = "fruit", "Fruit"
        DRINK = "drink", "Drink"
        SNACK = "snack", "Snack"
        ADDON = "addon", "Addon"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    group = models.CharField(max_length=20, choices=Group.choices)
    price = models.PositiveIntegerField(validators=[MinValueValidator(0)])
    required = models.BooleanField(default=True)
    image = models.ImageField(upload_to="builder-items/", blank=True, null=True)

    class Meta:
        ordering = ["group", "name"]
        verbose_name = "Builder Item"
        verbose_name_plural = "Builder Items"

    def __str__(self) -> str:
        return f"{self.name} ({self.group})"

# Create your models here.
