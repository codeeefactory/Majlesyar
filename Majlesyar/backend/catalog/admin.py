from django.contrib import admin

from .models import BuilderItem, Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "icon")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "available", "featured")
    list_filter = ("available", "featured", "categories")
    search_fields = ("name", "description", "contents")
    filter_horizontal = ("categories",)
    list_editable = ("available", "featured")


@admin.register(BuilderItem)
class BuilderItemAdmin(admin.ModelAdmin):
    list_display = ("name", "group", "price", "required")
    list_filter = ("group", "required")
    search_fields = ("name",)

# Register your models here.
