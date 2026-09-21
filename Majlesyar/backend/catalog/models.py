import uuid
from urllib.parse import unquote, urlsplit

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from .image_utils import (
    build_product_image_upload_path,
    derive_image_label,
    image_extension_validator,
    prepare_image_for_existing_path,
    product_image_storage,
)
from .image_variants import ensure_product_image_variants
from .three_d import build_asset_3d_upload_path, validate_glb_file
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


class Asset3DStatus(models.TextChoices):
    QUEUED = "queued", "در صف ساخت"
    MISSING = "missing", "ساخته نشده"
    PROCESSING = "processing", "در حال ساخت"
    READY = "ready", "آماده"
    FAILED = "failed", "خطا در ساخت"
PRODUCT_INPUT_MODE_PHOTO_PROCESSING = "photo_processing"


def normalize_product_public_path(value: str | None) -> str:
    raw_value = str(value or "").strip()
    if not raw_value:
        return ""

    parsed = urlsplit(raw_value if "://" in raw_value else f"https://majlesyar.com/{raw_value.lstrip('/')}")
    if parsed.hostname and parsed.hostname.lower() not in {"majlesyar.com", "www.majlesyar.com"}:
        raise ValidationError("آدرس کامل محصول باید متعلق به دامنه majlesyar.com باشد.")

    path = unquote(parsed.path or "")
    path = "/" + "/".join(part for part in path.split("/") if part)
    path = path.rstrip("/") or "/"
    first_part = path.strip("/").split("/", 1)[0].lower()
    if first_part in {"api", "majmanage", "media", "static", "product"}:
        raise ValidationError("این پیشوند برای آدرس محصول مجاز نیست. از مسیرهایی مانند /pack/... استفاده کنید.")
    if path == "/":
        raise ValidationError("آدرس صفحه اصلی را نمی‌توان برای محصول استفاده کرد.")
    return path


ADDITIONAL_EVENT_CATEGORY_DEFINITIONS = (
    ("food", "منوی فود", "🍽️"),
    ("food-charcuterie-board", "چاکوتری برد", "🧀"),
    ("food-ashe-rashteh", "آش رشته", "🍲"),
    ("food-dessert", "دسر", "🍰"),
    ("food-juice", "آبمیوه", "🧃"),
    ("shaleh-zard", "شله زرد", "🍮"),
    ("pack", "پک پذیرایی", "📦"),
    ("pack-personal", "پک پذیرایی شخصی", "📦"),
    ("pack-memorial-luxury", "پک ترحیم لوکس", "🕯️"),
    ("halva-khorma-luxury", "حلوا و خرمای لوکس", "🍯"),
    ("memorial-wreaths", "تاج گل ترحیم", "🖤"),
    ("bouquets", "دسته گل", "💐"),
    ("congratulatory-wreaths", "تاج گل تبریک", "🎉"),
    ("flower-congratulation-wreaths", "تاج گل تبریک", "🎉"),
    ("flower-funeral-bouquet", "دسته گل ترحیم", "🖤"),
    ("flower-box", "باکس گل", "🌸"),
)
ALL_EVENT_CATEGORY_DEFINITIONS = tuple(
    dict.fromkeys(EVENT_CATEGORY_DEFINITIONS + ADDITIONAL_EVENT_CATEGORY_DEFINITIONS)
)


EXTRA_EVENT_KEYWORDS = (
    ("food-charcuterie-board", ("چاکوتری", "charcuterie", "cheese board", "میز مزه")),
    ("food-ashe-rashteh", ("آش", "اش", "رشته", "ashe", "ash")),
    ("food-dessert", ("دسر", "dessert", "کیک", "شیرینی")),
    ("food-juice", ("آبمیوه", "ابمیوه", "juice", "نوشیدنی")),
    ("shaleh-zard", ("شله زرد", "شله‌زرد", "shole", "sholeh")),
    ("food", ("غذا", "فود", "خوراک", "پذیرایی", "food")),
    ("pack-memorial-luxury", ("پک ترحیم لوکس", "luxury memorial")),
    ("pack-personal", ("پک شخصی", "پک پذیرایی شخصی")),
    ("pack", ("پک", "بسته", "pack", "جعبه پذیرایی")),
    ("halva-khorma-luxury", ("حلوا لوکس", "خرما لوکس", "luxury halva")),
    ("memorial-wreaths", ("تاج گل ترحیم", "تاج ترحیم", "تاج گل ختم", "funeral wreath")),
    ("congratulatory-wreaths", ("تاج گل تبریک", "تاج تبریک", "congratulation wreath")),
    ("flower-funeral-bouquet", ("دسته گل ترحیم", "دسته گل تسلیت", "funeral bouquet")),
    ("flower-box", ("باکس گل", "جعبه گل", "flower box")),
    ("bouquets", ("دسته گل", "bouquet")),
)


def get_content_item_name(item) -> str:
    if isinstance(item, dict):
        return str(item.get("name") or "").strip()
    return str(item or "").strip()


def get_content_item_price(item) -> int | None:
    if not isinstance(item, dict):
        return None
    raw_price = item.get("price")
    if raw_price in (None, ""):
        return None
    try:
        price = int(raw_price)
    except (TypeError, ValueError):
        return None
    return price if price >= 0 else None


def get_content_item_names(contents: list | None) -> list[str]:
    return [name for item in (contents or []) if (name := get_content_item_name(item))]


def normalize_product_contents(contents: list | None) -> list[dict]:
    normalized = []
    for item in contents or []:
        name = get_content_item_name(item)
        if not name:
            continue
        normalized.append(
            {
                "name": name,
                "price": get_content_item_price(item),
            }
        )
    return normalized


def infer_event_types(name: str, description: str = "", contents: list | None = None) -> list[str]:
    haystack = " ".join(
        value
        for value in [
            _normalize_text(name),
            _normalize_text(description),
            _normalize_text(" ".join(get_content_item_names(contents))),
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

    keyword_map.extend(EXTRA_EVENT_KEYWORDS)

    detected: list[str] = []
    for slug, keywords in keyword_map:
        for keyword in keywords:
            if _normalize_text(keyword) in haystack:
                detected.append(slug)
                break
    return detected


AUTO_EVENT_CATEGORY_SLUGS = tuple(slug for slug, _name, _icon in ALL_EVENT_CATEGORY_DEFINITIONS)


def normalize_event_types(event_types: list[str] | None) -> list[str]:
    cleaned = []
    for item in event_types or []:
        slug = str(item).strip()
        if not slug:
            continue
        if slug == "defense":
            slug = "halva-khorma"
        if slug == "flower":
            slug = "party"
        cleaned.append(slug)
    return list(dict.fromkeys(cleaned))


def ensure_event_categories() -> None:
    for slug, name, icon in ALL_EVENT_CATEGORY_DEFINITIONS:
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

    if force:
        exact_event_types = list(dict.fromkeys(category_event_slugs))
        if exact_event_types != (product.event_types or []):
            product.event_types = exact_event_types
            Product.objects.filter(pk=product.pk).update(event_types=exact_event_types)
        return

    if not normalized_event_types and category_event_slugs:
        normalized_event_types = list(dict.fromkeys(category_event_slugs))

    if normalized_event_types != (product.event_types or []):
        product.event_types = normalized_event_types
        Product.objects.filter(pk=product.pk).update(event_types=normalized_event_types)

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
        verbose_name="رنگ",
        help_text="نکته: کد رنگ را وارد کنید (مثال: #F1C40F یا bg-primary/20).",
    )
    logo = models.ImageField(
        upload_to="category-logos/",
        blank=True,
        null=True,
        validators=[image_extension_validator],
        verbose_name="لوگو",
        help_text="راهنما: لوگو دسته بندی را با فرمت‌های jpg، jpeg، png، webp یا avif بارگذاری کنید.",
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

    class BuilderGroup(models.TextChoices):
        AUTO = "", "تشخیص خودکار"
        PACKAGING = "packaging", "بسته بندی"
        FRUIT = "fruit", "میوه"
        DRINK = "drink", "نوشیدنی"
        SNACK = "snack", "اسنک"
        ADDON = "addon", "افزودنی"
        PRODUCTS = "products", "محصولات آماده"

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
        upload_to=build_product_image_upload_path,
        storage=product_image_storage,
        max_length=500,
        blank=True,
        null=True,
        validators=[image_extension_validator],
        verbose_name="تصویر محصول",
        help_text="راهنما: تصویر محصول را با کیفیت مناسب و فرمت‌های jpg، jpeg، png، webp یا avif بارگذاری کنید. می توانید با گزینه پاک کردن، انتخاب تصویر را حذف کنید.",
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
    image_variants = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="نسخه‌های بهینه تصویر",
        help_text="اطلاعات نسخه‌های AVIF، WebP، JPEG و فایل اصلی برای نمایش سریع‌تر و واکنش‌گرا.",
    )
    model_3d = models.FileField(
        upload_to=build_asset_3d_upload_path,
        max_length=500,
        blank=True,
        null=True,
        validators=[validate_glb_file],
        verbose_name="مدل سه‌بعدی محصول (GLB)",
        help_text="مدل GLB تاییدشده را بارگذاری کنید؛ در نبود آن پیش‌نمایش حجمی از عکس محصول ساخته می‌شود.",
    )
    model_3d_status = models.CharField(
        max_length=20,
        choices=Asset3DStatus.choices,
        default=Asset3DStatus.MISSING,
        verbose_name="وضعیت مدل سه‌بعدی",
    )
    model_3d_metadata = models.JSONField(default=dict, blank=True, verbose_name="اطلاعات تولید مدل سه‌بعدی")
    model_3d_error = models.TextField(blank=True, default="", verbose_name="خطای تولید مدل سه‌بعدی")
    public_path = models.CharField(
        max_length=500,
        unique=True,
        blank=True,
        verbose_name="آدرس کامل محصول",
        help_text=(
            "کل آدرس یا مسیر را وارد کنید؛ مثل https://majlesyar.com/pack/my-pack یا /pack/my-pack. "
            "مسیرهای /product مجاز نیستند."
        ),
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
    is_temporary = models.BooleanField(
        default=False,
        verbose_name="محصول موقت (عدم نمایش در گوگل)",
        help_text=(
            "راهنما: برای محصول آزمایشی فعال کنید. صفحه محصول در سایت قابل بررسی می‌ماند، "
            "اما به موتورهای جستجو دستور داده می‌شود آن را ایندکس یا دنبال نکنند."
        ),
    )
    show_in_builder = models.BooleanField(
        default=True,
        verbose_name="نمایش در سازنده پک",
        help_text="نکته: اگر فعال باشد، این محصول در صفحه ساخت پک اختصاصی (/builder) قابل انتخاب است.",
    )
    builder_group = models.CharField(
        max_length=20,
        choices=BuilderGroup.choices,
        blank=True,
        default=BuilderGroup.AUTO,
        verbose_name="بخش محصول در سازنده پک",
        help_text="نکته: با حالت تشخیص خودکار، بخش محصول از دسته‌بندی و متن محصول حدس زده می‌شود.",
    )
    builder_required = models.BooleanField(
        default=False,
        verbose_name="انتخاب اجباری در سازنده پک",
        help_text="نکته: برای محصولات معمولاً خاموش بماند؛ فقط وقتی روشن کنید که این محصول باید در پک انتخاب شود.",
    )
    builder_display_order = models.PositiveIntegerField(
        default=100,
        validators=[MinValueValidator(1)],
        verbose_name="ترتیب نمایش در سازنده پک",
        help_text="نکته: عدد کوچکتر یعنی نمایش زودتر در صفحه ساخت پک.",
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
        previous_image_variants = {}
        previous_contents = []
        previous = None
        if self.pk:
            previous = Product.objects.filter(pk=self.pk).only(
                "image",
                "image_alt",
                "image_name",
                "image_variants",
                "contents",
            ).first()
            if previous and previous.image:
                previous_default_label = derive_image_label(previous.image.name)
                previous_image_name = previous.image.name
            if previous:
                previous_image_variants = previous.image_variants or {}
                previous_contents = previous.contents or []

        incoming_image_is_uncommitted = bool(
            self.image and not getattr(self.image, "_committed", True)
        )
        if previous_image_name and incoming_image_is_uncommitted:
            replacement = prepare_image_for_existing_path(self.image.file, previous_image_name)
            saved_name = self.image.storage.save(previous_image_name, replacement)
            self.image.name = saved_name
            self.image._committed = True
            self._image_content_changed = True

        if not isinstance(self.contents, list):
            self.contents = []
        self.contents = normalize_product_contents(self.contents)
        contents_changed = self.contents != normalize_product_contents(previous_contents)

        if not isinstance(self.event_types, list):
            self.event_types = []
        cleaned_event_types = [str(item).strip() for item in self.event_types if str(item).strip()]
        if not cleaned_event_types:
            inferred = infer_event_types(self.name or "", self.description or "", self.contents or [])
            if inferred:
                cleaned_event_types = inferred
        self.event_types = cleaned_event_types

        # Keep a stable lookup slug while public URLs remain fully manager-controlled.
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

        requested_path = normalize_product_public_path(self.public_path)
        base_path = requested_path or f"/pack/{self.url_slug}"
        candidate_path = base_path
        suffix = 2
        while Product.objects.exclude(pk=self.pk).filter(public_path=candidate_path).exists():
            candidate_path = f"{base_path}-{suffix}"
            suffix += 1
        self.public_path = candidate_path

        if self.image:
            derived_label = derive_image_label(self.image.name)
            if derived_label and (not self.image_name or self.image_name == previous_default_label):
                self.image_name = derived_label
            if derived_label and (not self.image_alt or self.image_alt == previous_default_label):
                self.image_alt = derived_label

        current_image_name = self.image.name if self.image else ""
        image_changed = current_image_name != previous_image_name or bool(
            getattr(self, "_image_content_changed", False)
        )
        if self.model_3d and self.model_3d_status == Asset3DStatus.MISSING:
            self.model_3d_status = Asset3DStatus.READY
            self.model_3d_error = ""
        elif not self.model_3d and self.model_3d_status == Asset3DStatus.READY:
            self.model_3d_status = Asset3DStatus.MISSING
            self.model_3d_metadata = {}
        super().save(*args, **kwargs)
        sync_product_categories(self)

        should_refresh_variants = image_changed or bool(self.image and not self.image_variants) or bool(
            not self.image and previous_image_variants
        )
        if should_refresh_variants:
            image_variants = ensure_product_image_variants(self, force=image_changed)
            if image_variants != (self.image_variants or {}):
                self.image_variants = image_variants
                Product.objects.filter(pk=self.pk).update(image_variants=image_variants)

        input_mode = getattr(self, "_input_mode", PRODUCT_INPUT_MODE_NORMAL)
        if input_mode == PRODUCT_INPUT_MODE_PHOTO_PROCESSING and self.image:
            if image_changed and hasattr(self.image, "path"):
                analysis = analyze_product_image(self.image.path)
                save_prediction_result(self, analysis)
                update_fields = {"photo_analysis": self.photo_analysis}
                if self.contents:
                    self.contents = normalize_product_contents(self.contents)
                    update_fields["contents"] = self.contents
                if self.event_types:
                    update_fields["event_types"] = self.event_types
                Product.objects.filter(pk=self.pk).update(**update_fields)
                sync_product_categories(self)

        if image_changed or contents_changed:
            from .media_processing import schedule_asset_processing

            schedule_asset_processing(self, image_changed=image_changed)
        self._image_content_changed = False

    class Meta:
        ordering = ["-featured", "name"]
        verbose_name = "محصول"
        verbose_name_plural = "محصولات"

    def __str__(self) -> str:
        return self.name


class CustomerReview(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="شناسه",
        help_text="نکته: این شناسه به صورت خودکار ساخته می شود.",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        related_name="customer_reviews",
        blank=True,
        null=True,
        verbose_name="محصول",
        help_text="اگر نظر مربوط به یک محصول خاص است، آن محصول را انتخاب کنید.",
    )
    customer_name = models.CharField(
        max_length=120,
        verbose_name="نام مشتری",
        help_text="نام نمایشی مشتری برای سایت.",
    )
    customer_city = models.CharField(
        max_length=80,
        blank=True,
        default="",
        verbose_name="شهر",
        help_text="شهر یا محدوده مشتری، اختیاری.",
    )
    title = models.CharField(
        max_length=160,
        blank=True,
        default="",
        verbose_name="عنوان نظر",
        help_text="عنوان کوتاه برای نظر مشتری.",
    )
    comment = models.TextField(
        verbose_name="متن نظر",
        help_text="متن کامل بازخورد مشتری.",
    )
    rating = models.PositiveSmallIntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="امتیاز",
        help_text="امتیاز از ۱ تا ۵.",
    )
    is_approved = models.BooleanField(
        default=True,
        verbose_name="تایید شده",
        help_text="فقط نظرهای تایید شده در سایت نمایش داده می شوند.",
    )
    is_featured = models.BooleanField(
        default=False,
        verbose_name="ویژه",
        help_text="نظرهای ویژه در بخش بازخورد مشتریان اولویت دارند.",
    )
    display_order = models.PositiveIntegerField(
        default=100,
        validators=[MinValueValidator(1)],
        verbose_name="ترتیب نمایش",
        help_text="عدد کوچکتر یعنی نمایش زودتر.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="زمان ایجاد",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="آخرین بروزرسانی",
    )

    class Meta:
        ordering = ["display_order", "-is_featured", "-created_at"]
        verbose_name = "نظر مشتری"
        verbose_name_plural = "نظرهای مشتریان"

    def __str__(self) -> str:
        return f"{self.customer_name} - {self.rating}/5"


class InternalLinkSource(models.Model):
    """Marks a page whose internal-link list is explicitly managed, even when empty."""

    path = models.CharField(max_length=500, primary_key=True, verbose_name="مسیر صفحه")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["path"]
        verbose_name = "منبع مدیریت لینک داخلی"
        verbose_name_plural = "منابع مدیریت لینک داخلی"

    def __str__(self) -> str:
        return self.path


class InternalLink(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_path = models.CharField(
        max_length=500,
        db_index=True,
        verbose_name="صفحه نمایش‌دهنده",
        help_text="مسیر صفحه‌ای که کارت در آن نمایش داده شود؛ مثل /pack/memorial.",
    )
    label = models.CharField(max_length=255, verbose_name="عنوان کارت")
    target_url = models.CharField(
        max_length=500,
        verbose_name="لینک مقصد",
        help_text="مسیر داخلی مقصد؛ مثل /builder یا /flower/memorial-wreaths.",
    )
    image = models.ImageField(
        upload_to="internal-links/%Y/%m/",
        blank=True,
        null=True,
        validators=[image_extension_validator],
        verbose_name="تصویر کارت",
        help_text="تصویر را هر زمان خواستید جایگزین یا پاک کنید.",
    )
    image_alt = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="متن جایگزین تصویر (Alt)",
        help_text="توضیح کوتاه و دقیق تصویر برای دسترس‌پذیری و سئو.",
    )
    position = models.PositiveIntegerField(default=100, validators=[MinValueValidator(1)], verbose_name="ترتیب نمایش")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        super().clean()
        self.source_path = self._normalize_internal_path(self.source_path, "صفحه نمایش‌دهنده")
        self.target_url = self._normalize_internal_path(self.target_url, "لینک مقصد")

    def save(self, *args, **kwargs):
        self.source_path = self._normalize_internal_path(self.source_path, "صفحه نمایش‌دهنده")
        self.target_url = self._normalize_internal_path(self.target_url, "لینک مقصد")
        super().save(*args, **kwargs)
        InternalLinkSource.objects.using(self._state.db).get_or_create(path=self.source_path)

    @staticmethod
    def _normalize_internal_path(value: str, label: str) -> str:
        raw_value = str(value or "").strip()
        parsed = urlsplit(raw_value if "://" in raw_value else f"https://majlesyar.com/{raw_value.lstrip('/')}")
        if parsed.hostname and parsed.hostname.lower() not in {"majlesyar.com", "www.majlesyar.com"}:
            raise ValidationError({"target_url": f"{label} باید داخل majlesyar.com باشد."})
        path = "/" + "/".join(part for part in unquote(parsed.path or "").split("/") if part)
        return path.rstrip("/") or "/"

    class Meta:
        ordering = ["source_path", "position", "created_at"]
        constraints = [
            models.UniqueConstraint(fields=["source_path", "target_url"], name="unique_internal_link_per_source"),
        ]
        verbose_name = "لینک داخلی تصویری"
        verbose_name_plural = "لینک‌های داخلی تصویری"

    def __str__(self) -> str:
        return f"{self.source_path} ← {self.label}"


class PageProductPlacement(models.Model):
    class PageType(models.TextChoices):
        HOME = "home", "صفحه اصلی"
        SHOP = "shop", "فروشگاه"
        EVENT = "event", "صفحه مراسم"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="شناسه",
        help_text="این شناسه به‌صورت خودکار ساخته می‌شود.",
    )
    page_type = models.CharField(
        max_length=24,
        choices=PageType.choices,
        verbose_name="نوع صفحه",
        help_text="مشخص می‌کند این محصول در کدام نوع صفحه مرتب شده است.",
    )
    page_slug = models.CharField(
        max_length=128,
        blank=True,
        default="",
        verbose_name="شناسه صفحه",
        help_text="برای صفحه‌های رویداد، اسلاگ رویداد و برای صفحه‌های ثابت کلید داخلی صفحه ذخیره می‌شود.",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="page_placements",
        verbose_name="محصول",
        help_text="محصولی که در این صفحه نمایش داده می‌شود.",
    )
    position = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name="ترتیب نمایش",
        help_text="عدد کوچکتر یعنی نمایش زودتر در همان صفحه.",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین به‌روزرسانی")

    class Meta:
        ordering = ["page_type", "page_slug", "position", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["page_type", "page_slug", "product"],
                name="unique_page_product_placement",
            ),
        ]
        verbose_name = "چیدمان محصول در صفحه"
        verbose_name_plural = "چیدمان محصولات در صفحه‌ها"

    def __str__(self) -> str:
        return f"{self.page_type}:{self.page_slug or 'default'} -> {self.product.name} ({self.position})"


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
        help_text="نکته: بارگذاری تصویر با فرمت‌های jpg، jpeg، png، webp یا avif برای نمایش بهتر این آیتم.",
    )
    photo_analysis = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="نتیجه تحلیل تصویر",
        help_text="خروجی تحلیل خودکار تصویر و مشخصات آیتم ذخیره‌شده روی سرور.",
    )
    model_3d = models.FileField(
        upload_to=build_asset_3d_upload_path,
        max_length=500,
        blank=True,
        null=True,
        validators=[validate_glb_file],
        verbose_name="مدل سه‌بعدی آیتم (GLB)",
        help_text="اختیاری؛ اگر خالی باشد تصویر آیتم به‌صورت پیش‌نمایش حجمی نمایش داده می‌شود.",
    )
    model_3d_status = models.CharField(
        max_length=20,
        choices=Asset3DStatus.choices,
        default=Asset3DStatus.MISSING,
        verbose_name="وضعیت مدل سه‌بعدی",
    )
    model_3d_metadata = models.JSONField(default=dict, blank=True, verbose_name="اطلاعات تولید مدل سه‌بعدی")
    model_3d_error = models.TextField(blank=True, default="", verbose_name="خطای تولید مدل سه‌بعدی")

    def save(self, *args, **kwargs):
        previous_image_name = ""
        previous_identity = None
        if self.pk:
            previous = BuilderItem.objects.filter(pk=self.pk).only("image", "name", "group", "price").first()
            if previous:
                previous_image_name = previous.image.name if previous.image else ""
                previous_identity = (previous.name, previous.group, previous.price)

        incoming_image_is_uncommitted = bool(self.image and not getattr(self.image, "_committed", True))
        current_image_name = self.image.name if self.image else ""
        image_changed = incoming_image_is_uncommitted or current_image_name != previous_image_name
        identity_changed = previous_identity != (self.name, self.group, self.price)
        if self.model_3d and self.model_3d_status == Asset3DStatus.MISSING:
            self.model_3d_status = Asset3DStatus.READY
            self.model_3d_error = ""
        elif not self.model_3d and self.model_3d_status == Asset3DStatus.READY:
            self.model_3d_status = Asset3DStatus.MISSING
            self.model_3d_metadata = {}
        super().save(*args, **kwargs)
        if image_changed or identity_changed:
            from .media_processing import schedule_asset_processing

            schedule_asset_processing(self, image_changed=image_changed)

    class Meta:
        ordering = ["group", "name"]
        verbose_name = "آیتم سازنده پک"
        verbose_name_plural = "آیتم های سازنده پک"

    def __str__(self) -> str:
        return f"{self.name} ({self.group})"


class AssetProcessingJob(models.Model):
    class TargetType(models.TextChoices):
        PRODUCT = "product", "محصول"
        BUILDER_ITEM = "builder_item", "آیتم سازنده پک"

    class Status(models.TextChoices):
        PENDING = "pending", "در صف"
        RUNNING = "running", "در حال پردازش"
        SUCCEEDED = "succeeded", "موفق"
        FAILED = "failed", "ناموفق"
        SUPERSEDED = "superseded", "جایگزین شده"
        SKIPPED = "skipped", "رد شده"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    target_type = models.CharField(max_length=20, choices=TargetType.choices)
    target_id = models.UUIDField()
    source_image_name = models.CharField(max_length=500)
    source_sha256 = models.CharField(max_length=64)
    request_sha256 = models.CharField(max_length=64)
    requested_actions = models.JSONField(default=list, blank=True)
    input_metadata = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    attempts = models.PositiveSmallIntegerField(default=0)
    available_at = models.DateTimeField(default=timezone.now)
    locked_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True, default="")
    result = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["target_type", "target_id", "request_sha256"],
                name="unique_asset_processing_request",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "available_at"], name="asset_job_status_available"),
            models.Index(fields=["target_type", "target_id"], name="asset_job_target"),
        ]
        verbose_name = "وظیفه پردازش تصویر"
        verbose_name_plural = "وظایف پردازش تصاویر"

    def __str__(self) -> str:
        return f"{self.target_type}:{self.target_id} ({self.status})"
