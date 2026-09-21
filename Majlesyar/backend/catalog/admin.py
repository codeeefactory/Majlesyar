from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.http import content_disposition_header
from django.utils.html import format_html

from config.admin_mixins import PersianAdminFormMixin
from .image_variants import ensure_product_image_variants
from .three_d import generate_asset_3d
from .product_bundle import (
    BUNDLE_CONTENT_TYPE,
    BUNDLE_EXTENSION,
    MAX_BUNDLE_BYTES,
    ProductBundleError,
    export_product_bundle,
    import_product_bundle,
    product_bundle_filename,
)
from .models import (
    AUTO_EVENT_CATEGORY_SLUGS,
    AssetProcessingJob,
    BuilderItem,
    Category,
    CustomerReview,
    InternalLink,
    PageProductPlacement,
    Product,
    Tag,
)


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categories"].label = "صفحه‌های نمایش محصول"
        self.fields["categories"].help_text = "یک یا چند صفحه را انتخاب کنید؛ محصول فقط در همان صفحه‌ها نمایش داده می‌شود."

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance._input_mode = self.cleaned_data.get("input_mode") or Product.InputMode.NORMAL
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class ProductBundleUploadForm(forms.Form):
    product_bundle = forms.FileField(
        label="فایل پشتیبان محصول",
        help_text="فقط فایل امن با پسوند .mjlsyar و حداکثر ۶۴ مگابایت پذیرفته می‌شود.",
    )

    def clean_product_bundle(self):
        upload = self.cleaned_data["product_bundle"]
        if not upload.name.lower().endswith(BUNDLE_EXTENSION):
            raise forms.ValidationError("پسوند فایل باید .mjlsyar باشد.")
        if upload.size > MAX_BUNDLE_BYTES:
            raise forms.ValidationError("حجم فایل پشتیبان بیش از ۶۴ مگابایت است.")
        return upload


@admin.register(Category)
class CategoryAdmin(PersianAdminFormMixin, admin.ModelAdmin):
    list_display = ("name", "slug", "page_url", "icon", "color")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("page_url",)
    fieldsets = (
        (
            "اطلاعات دسته بندی",
            {
                "description": "راهنما: نام را واضح بنویسید و اسلاگ را انگلیسی و یکتا ثبت کنید.",
                "fields": ("name", "slug", "page_url", "icon", "color", "logo"),
            },
        ),
    )

    @admin.display(description="URL صفحه")
    def page_url(self, obj: Category | None) -> str:
        if not obj:
            return "پس از ذخیره دسته‌بندی نمایش داده می‌شود."

        from site_settings.models import SiteSetting

        pages = SiteSetting.load().event_pages or []
        page = next(
            (
                item
                for item in pages
                if isinstance(item, dict)
                and str(item.get("slug") or item.get("id") or "").strip() == obj.slug
            ),
            None,
        )
        route_path = str((page or {}).get("route_path") or f"/events/{obj.slug}").strip()
        if not route_path.startswith("/"):
            route_path = f"/{route_path}"
        return format_html(
            '<a href="https://majlesyar.com{}" target="_blank" rel="noopener noreferrer" dir="ltr">{}</a>',
            route_path,
            route_path,
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
    change_form_template = "admin/catalog/product/change_form.html"
    change_list_template = "admin/catalog/product/change_list.html"
    EVENT_CATEGORY_SLUGS = AUTO_EVENT_CATEGORY_SLUGS
    list_display = (
        "name",
        "url_slug",
        "price",
        "available",
        "is_temporary",
        "featured",
        "show_in_builder",
        "builder_group",
        "updated_at",
    )
    list_filter = ()
    search_fields = ("name", "url_slug", "description", "contents", "image_name", "image_alt", "tags__name")
    filter_horizontal = ("categories", "tags")
    list_editable = ("available", "featured", "show_in_builder", "builder_group")
    readonly_fields = (
        "image_preview",
        "photo_analysis",
        "model_3d_status",
        "model_3d_metadata",
        "model_3d_error",
        "created_at",
        "updated_at",
    )
    actions = ("regenerate_image_variants", "generate_3d_models")
    fieldsets = (
        (
            "اطلاعات اصلی",
            {
                "description": "راهنما: نام، توضیحات و اطلاعات تصویر را کامل و واضح وارد کنید.",
                "fields": (
                    "input_mode",
                    "name",
                    "url_slug",
                    "public_path",
                    "description",
                    "image",
                    "image_preview",
                    "image_name",
                    "image_alt",
                    "photo_analysis",
                    "model_3d",
                    "model_3d_status",
                    "model_3d_metadata",
                    "model_3d_error",
                ),
            },
        ),
        (
            "قیمت و وضعیت",
            {
                "description": "راهنما: قیمت را به تومان وارد کنید. اگر قیمت توافقی است، آن را خالی بگذارید.",
                "fields": ("price", "available", "is_temporary", "featured"),
            },
        ),
        (
            "دسته بندی و محتوا",
            {
                "description": "صفحه‌های نمایش را دقیق انتخاب کنید؛ این انتخاب مرجع قطعی نمایش محصول است.",
                "fields": ("categories", "tags", "contents"),
            },
        ),
        (
            "نمایش در سازنده پک اختصاصی",
            {
                "description": "از این بخش مشخص کنید محصول در صفحه /builder به عنوان گزینه قابل افزودن به پک نمایش داده شود یا نه.",
                "fields": ("show_in_builder", "builder_group", "builder_required", "builder_display_order"),
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

    def get_urls(self):
        custom_urls = [
            path(
                "import-mjlsyar/",
                self.admin_site.admin_view(self.import_mjlsyar_view),
                name="catalog_product_import_mjlsyar",
            ),
            path(
                "<path:object_id>/export-mjlsyar/",
                self.admin_site.admin_view(self.export_mjlsyar_view),
                name="catalog_product_export_mjlsyar",
            ),
        ]
        return custom_urls + super().get_urls()

    def export_mjlsyar_view(self, request, object_id):
        product = self.get_object(request, object_id)
        if product is None:
            raise Http404
        if not self.has_view_or_change_permission(request, product):
            raise PermissionDenied
        try:
            payload = export_product_bundle(product)
        except ProductBundleError as exc:
            self.message_user(request, str(exc), level=messages.ERROR)
            return redirect(reverse("admin:catalog_product_change", args=(product.pk,)))

        filename = product_bundle_filename(product)
        response = HttpResponse(payload, content_type=BUNDLE_CONTENT_TYPE)
        response.headers["Content-Disposition"] = content_disposition_header(True, filename)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "private, no-store"
        return response

    def import_mjlsyar_view(self, request):
        if not self.has_add_permission(request):
            raise PermissionDenied
        form = ProductBundleUploadForm(request.POST or None, request.FILES or None)
        if request.method == "POST" and form.is_valid():
            upload = form.cleaned_data["product_bundle"]
            try:
                product = import_product_bundle(upload.read())
            except ProductBundleError as exc:
                form.add_error("product_bundle", str(exc))
            else:
                self.message_user(request, f"محصول «{product.name}» با موفقیت از فایل پشتیبان ساخته شد.")
                return redirect(reverse("admin:catalog_product_change", args=(product.pk,)))

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "افزودن محصول از فایل .mjlsyar",
            "form": form,
        }
        return TemplateResponse(request, "admin/catalog/product/import_mjlsyar.html", context)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        product: Product = form.instance
        # Admin category selection is authoritative. This prevents one product
        # from leaking into unrelated event pages through stale inferred values.
        from .models import sync_product_categories

        sync_product_categories(product, force=True)

    @admin.action(description="Regenerate optimized image variants")
    def regenerate_image_variants(self, request, queryset):
        processed = 0
        skipped = 0
        for product in queryset:
            if not product.image:
                skipped += 1
                continue
            metadata = ensure_product_image_variants(product, force=True)
            Product.objects.filter(pk=product.pk).update(image_variants=metadata)
            processed += 1

        if processed:
            self.message_user(
                request,
                f"Optimized variants regenerated for {processed} product image(s).",
            )
        if skipped:
            self.message_user(
                request,
                f"{skipped} product(s) were skipped because they do not have an image.",
            )

    @admin.action(description="ساخت مدل سه‌بعدی با سرویس ML")
    def generate_3d_models(self, request, queryset):
        processed = 0
        failed = 0
        for product in queryset:
            try:
                generate_asset_3d(product, force=True)
                processed += 1
            except Exception:
                failed += 1
        if processed:
            self.message_user(request, f"مدل سه‌بعدی {processed} محصول ساخته شد.")
        if failed:
            self.message_user(
                request,
                f"ساخت مدل سه‌بعدی {failed} محصول ناموفق بود؛ جزئیات داخل محصول ثبت شد.",
                level=messages.ERROR,
            )

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


@admin.register(CustomerReview)
class CustomerReviewAdmin(PersianAdminFormMixin, admin.ModelAdmin):
    list_display = (
        "customer_name",
        "rating",
        "product",
        "is_approved",
        "is_featured",
        "display_order",
        "created_at",
    )

    list_filter = ()
    list_editable = ("is_approved", "is_featured", "display_order")
    search_fields = ("customer_name", "customer_city", "title", "comment", "product__name")
    autocomplete_fields = ("product",)
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            "اطلاعات نظر",
            {
                "description": "نظر مشتری را دقیق ثبت کنید و فقط موارد تایید شده را در سایت نمایش دهید.",
                "fields": ("product", "customer_name", "customer_city", "title", "comment", "rating"),
            },
        ),
        (
            "نمایش در سایت",
            {
                "fields": ("is_approved", "is_featured", "display_order"),
            },
        ),
        (
            "زمان بندی",
            {
                "fields": ("created_at", "updated_at"),
            },
        ),
    )


@admin.register(InternalLink)
class InternalLinkAdmin(PersianAdminFormMixin, admin.ModelAdmin):
    list_display = ("label", "source_page", "target_page", "position", "is_active", "image_preview")
    list_display_links = ("label", "source_page", "target_page")
    list_filter = ("is_active", "source_path")
    list_editable = ("position", "is_active")
    search_fields = ("label", "source_path", "target_url", "image_alt")
    readonly_fields = ("image_preview", "created_at", "updated_at")
    save_on_top = True
    list_per_page = 100
    fieldsets = (
        (
            "مسیر و متن لینک",
            {
                "description": (
                    "صفحه نمایش‌دهنده یعنی لینکی که کارت در آن دیده می‌شود. "
                    "عنوان و مقصد را تغییر دهید یا برای حذف موقت، «فعال» را خاموش کنید."
                ),
                "fields": ("source_path", "label", "target_url", "position", "is_active"),
            },
        ),
        (
            "تصویر اختیاری کارت",
            {
                "fields": ("image", "image_preview", "image_alt"),
            },
        ),
        (
            "زمان‌ها",
            {
                "classes": ("collapse",),
                "fields": ("created_at", "updated_at"),
            },
        ),
    )

    @admin.display(description="نمایش در صفحه", ordering="source_path")
    def source_page(self, obj: InternalLink) -> str:
        return format_html('<span dir="ltr">{}</span>', obj.source_path)

    @admin.display(description="مقصد لینک", ordering="target_url")
    def target_page(self, obj: InternalLink) -> str:
        return format_html('<span dir="ltr">{}</span>', obj.target_url)

    @admin.display(description="پیش‌نمایش")
    def image_preview(self, obj: InternalLink | None) -> str:
        if not obj or not obj.image:
            return "—"
        return format_html(
            '<img src="{}" alt="{}" style="width:120px;height:80px;object-fit:cover;border-radius:12px" />',
            obj.image.url,
            obj.image_alt or obj.label,
        )


@admin.register(BuilderItem)
class BuilderItemAdmin(PersianAdminFormMixin, admin.ModelAdmin):
    list_display = ("name", "group", "price", "required", "model_3d_status")
    list_filter = ()
    search_fields = ("name",)
    readonly_fields = ("photo_analysis", "model_3d_status", "model_3d_metadata", "model_3d_error")
    fieldsets = (
        (
            "اطلاعات آیتم",
            {
                "description": "راهنما: اطلاعات این آیتم را کامل وارد کنید تا در ساخت پک سفارشی درست نمایش داده شود.",
                "fields": (
                    "name",
                    "group",
                    "price",
                    "required",
                    "image",
                    "photo_analysis",
                    "model_3d",
                    "model_3d_status",
                    "model_3d_metadata",
                    "model_3d_error",
                ),
            },
        ),
    )


@admin.register(AssetProcessingJob)
class AssetProcessingJobAdmin(admin.ModelAdmin):
    list_display = ("target_type", "target_id", "status", "attempts", "created_at", "finished_at")
    list_filter = ("target_type", "status")
    search_fields = ("target_id", "source_image_name", "source_sha256", "error")
    ordering = ("-created_at",)
    readonly_fields = (
        "id",
        "target_type",
        "target_id",
        "source_image_name",
        "source_sha256",
        "request_sha256",
        "requested_actions",
        "input_metadata",
        "status",
        "attempts",
        "available_at",
        "locked_at",
        "finished_at",
        "error",
        "result",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(PageProductPlacement)
class PageProductPlacementAdmin(PersianAdminFormMixin, admin.ModelAdmin):
    list_display = ("page_type", "page_slug", "position", "product")
    list_filter = ()
    search_fields = ("page_slug", "product__name", "product__url_slug")
    ordering = ("page_type", "page_slug", "position")
    autocomplete_fields = ("product",)
    fieldsets = (
        (
            "چیدمان محصول در صفحه",
            {
                "description": "برای هر صفحه، محصولات را با ترتیب دقیق ذخیره کنید تا وب‌سایت و اپ دسکتاپ از یک چیدمان مشترک استفاده کنند.",
                "fields": ("page_type", "page_slug", "product", "position"),
            },
        ),
    )
