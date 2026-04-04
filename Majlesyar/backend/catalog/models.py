import uuid

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.text import slugify

from .image_utils import derive_image_label, image_extension_validator
from vision.service import analyze_product_image, save_prediction_result


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    text = str(value)
    replacements = {
        "ي": "ی",
        "ك": "ک",
        "ۀ": "ه",
        "ة": "ه",
        "ؤ": "و",
        "إ": "ا",
        "أ": "ا",
        "آ": "ا",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text.lower()


EVENT_CATEGORY_DEFINITIONS = (
    ("conference", "فینگر فود", "🍢"),
    ("memorial", "ترحیم", "🕯️"),
    ("halva-khorma", "حلوا و خرما", "🍯"),
    ("party", "گل", "💐"),
)
PRODUCT_INPUT_MODE_NORMAL = "normal"
PRODUCT_INPUT_MODE_PHOTO_PROCESSING = "photo_processing"


def infer_event_types(name: str, description: str = "", contents: list[str] | None = None) -> list[str]:
    haystack = " ".join(
        value
        for value in [
            _normalize_text(name),
            _normalize_text(description),
            _normalize_text(" ".join(contents or [])),
        ]
        if value
    )
    if not haystack:
        return []

    keyword_map = [
        ("conference", ["فینگر", "فینگرفود", "finger", "fingerfood", "canape", "اسنک", "snack"]),
        ("memorial", ["ترحیم", "نذری", "ختم", "یادبود", "مجلس"]),
        ("halva-khorma", ["حلوا", "خرما", "حلوا و خرما"]),
        ("party", ["گل", "دسته گل", "گل آرایی", "گل‌آرایی", "bouquet", "flower"]),
    ]

    detected: list[str] = []
    for slug, keywords in keyword_map:
        for keyword in keywords:
            if _normalize_text(keyword) in haystack:
                detected.append(slug)
                break
    return detected


AUTO_EVENT_CATEGORY_SLUGS = tuple(slug for slug, _name, _icon in EVENT_CATEGORY_DEFINITIONS)


def normalize_event_types(event_types: list[str] | None) -> list[str]:
    cleaned = []
    for item in event_types or []:
        slug = str(item).strip()
        if not slug:
            continue
        if slug == "defense":
            slug = "halva-khorma"
        cleaned.append(slug)
    return list(dict.fromkeys(cleaned))


def ensure_event_categories() -> None:
    for slug, name, icon in EVENT_CATEGORY_DEFINITIONS:
        Category.objects.update_or_create(
            slug=slug,
            defaults={"name": name, "icon": icon},
        )

    legacy_category = Category.objects.filter(slug="defense").first()
    target_category = Category.objects.filter(slug="halva-khorma").first()
    if legacy_category and target_category and legacy_category.pk != target_category.pk:
        for product in legacy_category.products.exclude(categories=target_category):
            product.categories.add(target_category)
        legacy_category.delete()


def sync_product_categories(product: "Product", *, force: bool = False) -> None:
    ensure_event_categories()

    normalized_event_types = normalize_event_types(product.event_types)
    category_event_slugs = [
        slug
        for slug in product.categories.filter(slug__in=AUTO_EVENT_CATEGORY_SLUGS).values_list("slug", flat=True)
    ]

    if not normalized_event_types and category_event_slugs:
        normalized_event_types = list(dict.fromkeys(category_event_slugs))

    if normalized_event_types != (product.event_types or []):
        product.event_types = normalized_event_types
        Product.objects.filter(pk=product.pk).update(event_types=normalized_event_types)

    if product.categories.exists() and not force:
        return

    event_slugs = [slug for slug in normalized_event_types if slug in AUTO_EVENT_CATEGORY_SLUGS]
    if not event_slugs:
        event_slugs = infer_event_types(product.name or "", product.description or "", product.contents or [])
        event_slugs = [slug for slug in event_slugs if slug in AUTO_EVENT_CATEGORY_SLUGS]
        if event_slugs:
            product.event_types = event_slugs
            Product.objects.filter(pk=product.pk).update(event_types=event_slugs)
    if not event_slugs:
        return

    category_ids = list(
        Category.objects.filter(slug__in=event_slugs).values_list("id", flat=True)
    )
    if not category_ids:
        return

    existing_ids = set(product.categories.values_list("id", flat=True))
    missing_ids = [category_id for category_id in category_ids if category_id not in existing_ids]
    if missing_ids:
        product.categories.add(*missing_ids)


class Category(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="شناسه",
        help_text="نکته: این شناسه به صورت خودکار ساخته می شود.",
    )
    name = models.CharField(
        max_length=128,
        verbose_name="نام دسته بندی",
        help_text="نکته: نام نمایشی دسته بندی را وارد کنید.",
    )
    slug = models.SlugField(
        max_length=128,
        unique=True,
        verbose_name="اسلاگ",
        help_text="نکته: نسخه انگلیسی و یکتا برای آدرس دهی (مثال: economic).",
    )
    icon = models.CharField(
        max_length=32,
        blank=True,
        verbose_name="آیکون",
        help_text="نکته: می توانید ایموجی یا آیکون کوتاه وارد کنید.",
    )
    color = models.CharField(
        max_length=64,
        blank=True,
        default="",
        verbose_name="??????",
        help_text="????????: ???? ?????? (????????: #F1C40F ???? bg-primary/20).",
    )
    logo = models.ImageField(
        upload_to="category-logos/",
        blank=True,
        null=True,
        validators=[image_extension_validator],
        verbose_name="????????",
        help_text="????????????: ???????? ???????? ???????? ???? ???? ???????? jpg?? jpeg?? png ???? webp ???????????????? ????????.",
    )


    class Meta:
        ordering = ["name"]
        verbose_name = "دسته بندی"
        verbose_name_plural = "دسته بندی ها"

    def __str__(self) -> str:
        return self.name


class Tag(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="شناسه",
        help_text="نکته: این شناسه به صورت خودکار ساخته می شود.",
    )
    name = models.CharField(
        max_length=128,
        verbose_name="نام تگ",
        help_text="نکته: نام نمایشی تگ محصول را وارد کنید.",
    )
    slug = models.SlugField(
        max_length=128,
        unique=True,
        verbose_name="اسلاگ",
        help_text="نکته: نسخه انگلیسی و یکتا برای آدرس دهی (مثال: fast-delivery).",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "تگ"
        verbose_name_plural = "تگ ها"

    def __str__(self) -> str:
        return self.name


class Product(models.Model):
    class InputMode(models.TextChoices):
        NORMAL = PRODUCT_INPUT_MODE_NORMAL, "عادی"
        PHOTO_PROCESSING = PRODUCT_INPUT_MODE_PHOTO_PROCESSING, "با پردازش عکس"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="شناسه",
        help_text="نکته: این شناسه به صورت خودکار ساخته می شود.",
    )
    name = models.CharField(
        max_length=255,
        verbose_name="نام محصول",
        help_text="نکته: نام کامل محصول برای نمایش در سایت.",
    )
    url_slug = models.SlugField(
        max_length=180,
        unique=True,
        blank=True,
        verbose_name="آدرس محصول (URI)",
        help_text="نکته: آدرس محصول را به انگلیسی و یکتا وارد کنید (مثال: vip-pack).",
    )
    description = models.TextField(
        blank=True,
        verbose_name="توضیحات",
        help_text="نکته: توضیحات کوتاه و شفاف درباره محصول بنویسید.",
    )
    price = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name="قیمت (تومان)",
        help_text="نکته: مبلغ را به تومان وارد کنید. برای محصولات توافقی خالی بگذارید.",
    )
    categories = models.ManyToManyField(
        Category,
        related_name="products",
        blank=True,
        verbose_name="دسته بندی ها",
        help_text="نکته: دسته بندی های مرتبط با این محصول را انتخاب کنید.",
    )
    tags = models.ManyToManyField(
        Tag,
        related_name="products",
        blank=True,
        verbose_name="تگ ها",
        help_text="نکته: تگ های مرتبط با این محصول را انتخاب کنید.",
    )
    event_types = models.JSONField(
        default=list,
        blank=True,
        verbose_name="نوع مراسم",
        help_text="نکته: لیست نوع مراسم به صورت JSON (مثال: [\"conference\"]).",
    )
    contents = models.JSONField(
        default=list,
        blank=True,
        verbose_name="اقلام داخل پک",
        help_text="نکته: اقلام محصول را به صورت لیست JSON وارد کنید.",
    )
    image = models.ImageField(
        upload_to="products/",
        blank=True,
        null=True,
        validators=[image_extension_validator],
        verbose_name="تصویر محصول",
        help_text="راهنما: تصویر محصول را با کیفیت مناسب و فرمت‌های jpg، jpeg، png یا webp بارگذاری کنید. می توانید با گزینه پاک کردن، انتخاب تصویر را حذف کنید.",
    )
    image_alt = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="متن جایگزین تصویر (Alt)",
        help_text="راهنما: یک توضیح کوتاه و دقیق برای تصویر بنویسید تا در دسترس پذیری و سئو استفاده شود.",
    )
    image_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="نام تصویر",
        help_text="راهنما: یک نام خوانا برای تصویر وارد کنید (مثال: pak-terhim-luxury). این فیلد برای مدیریت بهتر تصاویر است.",
    )
    photo_analysis = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="نتیجه تحلیل تصویر",
        help_text="خروجی ساختارمند تشخیص محلی تصویر محصول.",
    )
    featured = models.BooleanField(
        default=False,
        verbose_name="ویژه",
        help_text="نکته: اگر فعال باشد، محصول در بخش ویژه نمایش داده می شود.",
    )
    available = models.BooleanField(
        default=True,
        verbose_name="موجود",
        help_text="نکته: اگر غیرفعال باشد، سفارش این محصول ممکن نیست.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="زمان ایجاد",
        help_text="نکته: این زمان به صورت خودکار ثبت می شود.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="آخرین بروزرسانی",
        help_text="نکته: این زمان بعد از هر ویرایش به صورت خودکار بروزرسانی می شود.",
    )

    def save(self, *args, **kwargs):
        previous_default_label = ""
        previous_image_name = ""
        previous = None
        if self.pk:
            previous = Product.objects.filter(pk=self.pk).only("image", "image_alt", "image_name").first()
            if previous and previous.image:
                previous_default_label = derive_image_label(previous.image.name)
                previous_image_name = previous.image.name

        if not isinstance(self.event_types, list):
            self.event_types = []
        cleaned_event_types = [str(item).strip() for item in self.event_types if str(item).strip()]
        if not cleaned_event_types:
            inferred = infer_event_types(self.name or "", self.description or "", self.contents or [])
            if inferred:
                cleaned_event_types = inferred
        self.event_types = cleaned_event_types

        # Normalize/generate URI slug so each product has a stable /product/{slug} path.
        base_slug = slugify((self.url_slug or "").strip()) if self.url_slug else ""
        if not base_slug:
            base_slug = slugify(self.name or "")
        if not base_slug:
            base_slug = f"product-{str(self.id or uuid.uuid4())[:8]}"

        candidate = base_slug
        suffix = 2
        while Product.objects.exclude(pk=self.pk).filter(url_slug=candidate).exists():
            candidate = f"{base_slug}-{suffix}"
            suffix += 1
        self.url_slug = candidate

        if self.image:
            derived_label = derive_image_label(self.image.name)
            if derived_label and (not self.image_name or self.image_name == previous_default_label):
                self.image_name = derived_label
            if derived_label and (not self.image_alt or self.image_alt == previous_default_label):
                self.image_alt = derived_label

        super().save(*args, **kwargs)
        sync_product_categories(self)

        input_mode = getattr(self, "_input_mode", PRODUCT_INPUT_MODE_NORMAL)
        if input_mode == PRODUCT_INPUT_MODE_PHOTO_PROCESSING and self.image:
            image_changed = self.image.name != previous_image_name
            if image_changed and hasattr(self.image, "path"):
                analysis = analyze_product_image(self.image.path)
                save_prediction_result(self, analysis)
                update_fields = {"photo_analysis": self.photo_analysis}
                if self.contents:
                    update_fields["contents"] = self.contents
                if self.event_types:
                    update_fields["event_types"] = self.event_types
                Product.objects.filter(pk=self.pk).update(**update_fields)
                sync_product_categories(self)

    class Meta:
        ordering = ["-featured", "name"]
        verbose_name = "محصول"
        verbose_name_plural = "محصولات"

    def __str__(self) -> str:
        return self.name


class BuilderItem(models.Model):
    class Group(models.TextChoices):
        PACKAGING = "packaging", "بسته بندی"
        FRUIT = "fruit", "میوه"
        DRINK = "drink", "نوشیدنی"
        SNACK = "snack", "اسنک"
        ADDON = "addon", "افزودنی"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="شناسه",
        help_text="نکته: این شناسه به صورت خودکار ساخته می شود.",
    )
    name = models.CharField(
        max_length=255,
        verbose_name="نام آیتم",
        help_text="نکته: نام آیتم سازنده پک را وارد کنید.",
    )
    group = models.CharField(
        max_length=20,
        choices=Group.choices,
        verbose_name="گروه",
        help_text="نکته: گروه آیتم را انتخاب کنید.",
    )
    price = models.PositiveIntegerField(
        validators=[MinValueValidator(0)],
        verbose_name="قیمت (تومان)",
        help_text="نکته: قیمت این آیتم را به تومان وارد کنید.",
    )
    required = models.BooleanField(
        default=True,
        verbose_name="اجباری",
        help_text="نکته: اگر فعال باشد انتخاب این آیتم برای ساخت پک الزامی است.",
    )
    image = models.ImageField(
        upload_to="builder-items/",
        blank=True,
        null=True,
        validators=[image_extension_validator],
        verbose_name="تصویر",
        help_text="نکته: بارگذاری تصویر با فرمت‌های jpg، jpeg، png یا webp برای نمایش بهتر این آیتم.",
    )

    class Meta:
        ordering = ["group", "name"]
        verbose_name = "آیتم سازنده پک"
        verbose_name_plural = "آیتم های سازنده پک"

    def __str__(self) -> str:
        return f"{self.name} ({self.group})"
