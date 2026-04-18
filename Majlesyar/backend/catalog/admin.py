from django import forms
from django.contrib import admin
from django.utils.html import format_html

from config.admin_mixins import PersianAdminFormMixin
from .models import BuilderItem, Category, Product, Tag


class ProductAdminForm(forms.ModelForm):
    input_mode = forms.ChoiceField(
        label="حالت افزودن محصول",
        choices=Product.InputMode.choices,
        required=False,
        initial=Product.InputMode.NORMAL,
        help_text="حالت عادی فقط اطلاعات واردشده را ذخیره می‌کند. حالت پردازش عکس، عناصر داخل تصویر را تشخیص می‌دهد.",
    )

    class Meta:
        model = Product
        fields = "__all__"

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance._input_mode = self.cleaned_data.get("input_mode") or Product.InputMode.NORMAL
        if commit:
            instance.save()
            self.save_m2m()
        return instance


@admin.register(Category)
class CategoryAdmin(PersianAdminFormMixin, admin.ModelAdmin):
    list_display = ("name", "slug", "icon", "color")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    fieldsets = (
        (
            "اطلاعات دسته بندی",
            {
                "description": "راهنما: نام را واضح بنویسید و اسلاگ را انگلیسی و یکتا ثبت کنید.",
                "fields": ("name", "slug", "icon", "color", "logo"),
            },
        ),
    )


@admin.register(Tag)
class TagAdmin(PersianAdminFormMixin, admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    fieldsets = (
        (
            "اطلاعات تگ",
            {
                "description": "راهنما: نام تگ را واضح بنویسید و اسلاگ را انگلیسی و یکتا ثبت کنید.",
                "fields": ("name", "slug"),
            },
        ),
    )


@admin.register(Product)
class ProductAdmin(PersianAdminFormMixin, admin.ModelAdmin):
    form = ProductAdminForm
    EVENT_CATEGORY_SLUGS = ("conference", "memorial", "halva-khorma", "party")
    list_display = ("name", "url_slug", "price", "available", "featured", "updated_at")
    list_filter = ("available", "featured", "categories", "tags")
    search_fields = ("name", "url_slug", "description", "contents", "image_name", "image_alt", "tags__name")
    prepopulated_fields = {"url_slug": ("name",)}
    filter_horizontal = ("categories", "tags")
    list_editable = ("available", "featured")
    readonly_fields = ("image_preview", "created_at", "updated_at")
    fieldsets = (
        (
            "اطلاعات اصلی",
            {
                "description": "راهنما: نام، توضیحات و اطلاعات تصویر را کامل و واضح وارد کنید.",
                "fields": (
                    "input_mode",
                    "name",
                    "url_slug",
                    "description",
                    "image",
                    "image_preview",
                    "image_name",
                    "image_alt",
                ),
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
                "description": "راهنما: دسته بندی، تگ، نوع مراسم و اقلام داخل پک را کامل و دقیق ثبت کنید.",
                "fields": ("categories", "tags", "event_types", "contents"),
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

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        product: Product = form.instance

        # If manager did not choose categories manually, auto-fill from event types
        # to keep product categories aligned with website event categories.
        if product.categories.exists():
            return

        event_slugs = [
            slug
            for slug in (product.event_types or [])
            if isinstance(slug, str) and slug in self.EVENT_CATEGORY_SLUGS
        ]
        if not event_slugs:
            return

        categories = Category.objects.filter(slug__in=event_slugs)
        if categories.exists():
            product.categories.add(*categories)

    @admin.display(description="پیش‌نمایش تصویر محصول")
    def image_preview(self, obj: Product | None) -> str:
        preview_image_url = obj.image.url if obj and obj.image else ""
        preview_label = obj.name if obj and obj.name else "پیش‌نمایش تصویر محصول"
        preview_state_class = "" if preview_image_url else " admin-image-preview-card--empty"
        preview_state_text = (
            "با انتخاب تصویر، پیش‌نمایش زنده اینجا نمایش داده می‌شود."
            if not preview_image_url
            else "تصویر فعلی محصول"
        )
        image_markup = (
            format_html(
                '<img src="{}" alt="" class="admin-image-preview-card__image" />',
                preview_image_url,
            )
            if preview_image_url
            else ""
        )
        return format_html(
            (
                '<div class="admin-image-preview-card{}" data-live-image-preview-card="image">'
                '<div class="admin-image-preview-card__eyebrow">{}</div>'
                '<div class="admin-image-preview-card__title">{}</div>'
                '<div class="admin-image-preview-card__media" data-live-image-preview-media="image">{}</div>'
                '<div class="admin-image-preview-card__caption" data-live-image-preview-caption="image">{}</div>'
                "</div>"
            ),
            preview_state_class,
            "پیش‌نمایش زنده",
            preview_label,
            image_markup,
            preview_state_text,
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
