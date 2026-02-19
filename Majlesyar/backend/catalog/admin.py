from django.contrib import admin

from config.admin_mixins import PersianAdminFormMixin
from .models import BuilderItem, Category, Product


@admin.register(Category)
class CategoryAdmin(PersianAdminFormMixin, admin.ModelAdmin):
    list_display = ("name", "slug", "icon")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    fieldsets = (
        (
            "اطلاعات دسته بندی",
            {
                "description": "راهنما: نام را واضح بنویسید و اسلاگ را انگلیسی و یکتا ثبت کنید.",
                "fields": ("name", "slug", "icon"),
            },
        ),
    )


@admin.register(Product)
class ProductAdmin(PersianAdminFormMixin, admin.ModelAdmin):
    list_display = ("name", "price", "available", "featured", "updated_at")
    list_filter = ("available", "featured", "categories")
    search_fields = ("name", "description", "contents", "image_name", "image_alt")
    autocomplete_fields = ("categories",)
    list_editable = ("available", "featured")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            "اطلاعات اصلی",
            {
                "description": "راهنما: نام، توضیحات و اطلاعات تصویر را کامل و واضح وارد کنید.",
                "fields": ("name", "description", "image", "image_name", "image_alt"),
            },
        ),
        (
            "قیمت و وضعیت",
            {
                "description": "راهنما: قیمت را به تومان وارد کنید. اگر قیمت توافقی است، آن را خالی بگذارید.",
                "fields": ("price", "available", "featured"),
            },
        ),
        (
            "دسته بندی و محتوا",
            {
                "description": "راهنما: دسته بندی، نوع مراسم و اقلام داخل پک را کامل و دقیق ثبت کنید.",
                "fields": ("categories", "event_types", "contents"),
            },
        ),
        (
            "زمان بندی",
            {
                "description": "نکته: این فیلدها به صورت خودکار مدیریت می شوند.",
                "fields": ("created_at", "updated_at"),
            },
        ),
    )


@admin.register(BuilderItem)
class BuilderItemAdmin(PersianAdminFormMixin, admin.ModelAdmin):
    list_display = ("name", "group", "price", "required")
    list_filter = ("group", "required")
    search_fields = ("name",)
    fieldsets = (
        (
            "اطلاعات آیتم",
            {
                "description": "راهنما: اطلاعات این آیتم را کامل وارد کنید تا در ساخت پک سفارشی درست نمایش داده شود.",
                "fields": ("name", "group", "price", "required", "image"),
            },
        ),
    )
