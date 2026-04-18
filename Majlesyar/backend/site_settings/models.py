from __future__ import annotations

from copy import deepcopy

from django.core.validators import MinValueValidator
from django.db import models

from catalog.image_utils import image_extension_validator


DEFAULT_SITE_TOP_NOTICE = {
    "title": "پرداخت در محل",
    "message": "با افتخار تنها مجموعه‌ای هستیم که ۸۰ درصد از مبلغ را در زمان تحویل دریافت می‌کنیم.",
    "badge": "۸۰٪ هنگام تحویل",
}

DEFAULT_HOMEPAGE_BENEFITS_SECTION = {
    "eyebrow": "تعهدهای مجلس‌یار",
    "title": "مزیت‌هایی که بعد از انتخاب محصول هم کنار شما می‌ماند",
    "items": [
        {
            "title": "تضمین ارسال به موقع",
            "description": "با افتخار تنها مجموعه‌ای هستیم که در ارسال به موقع تضمین می‌دهیم",
            "note": "در صورت دیر رسیدن تمامی سفارشات رایگان تحویل داده می‌شود",
        },
        {
            "title": "کیفیت عالی",
            "description": "در مجلس‌یار اقلام مورد نیاز، بعد از سفارش شما خریداری می‌شود، تا از تازگی و کیفیت اطمینان حاصل شود.",
            "note": "",
        },
        {
            "title": "قیمت منصفانه",
            "description": "با افتخار پیدا کردن محصولی پایین از قیمت مجلس‌یار تقریباً غیرممکن است.",
            "note": "",
        },
        {
            "title": "بهداشت",
            "description": "و در آخر با افتخار تمامی کارکنان مجلس‌یار دارای کارت بهداشت می‌باشند.",
            "note": "",
        },
    ],
}

DEFAULT_SITE_BRANDING = {
    "site_name": "مجلس یار",
    "site_alternate_name": "Majlesyar",
    "site_tagline": "پک‌های پذیرایی ویژه مراسمات",
    "logo_alt": "لوگوی مجلس یار",
    "meta_author": "مجلس یار",
    "default_meta_title": "سفارش آنلاین تاج گل، پک ترحیم و حلوا خرما (ارسال فوری)",
    "default_meta_description": "مجلس یار؛ مرجع خدمات مجالس ترحیم و تولد. سفارش آنلاین حلوا خرما، پک میوه، فینگر فود و تاج گل با پایین‌ترین قیمت و ارسال فوری. برای تضمین کیفیت، بخشی از وجه را هنگام تحویل بپردازید!",
    "default_meta_keywords": [
        "پک پذیرایی",
        "پک نذری",
        "کترینگ مراسم",
        "فینگر فود",
        "ترحیم",
        "گل مراسم",
        "مجلس یار",
        "حلوا و خرما",
    ],
    "admin_site_title": "پنل مدیریت مجلس یار",
    "admin_site_header": "مجلس یار",
    "admin_site_subheader": "مدیریت فروش و سفارش پک‌های پذیرایی",
    "admin_site_symbol": "inventory_2",
}

DEFAULT_THEME_PALETTE = {
    "primary": "#0C9FC7",
    "accent": "#D6A45B",
    "background": "#FDFBF7",
    "surface": "#FFFFFF",
    "foreground": "#24303A",
    "muted_foreground": "#5E6B78",
    "success": "#218A52",
    "warning": "#C98A10",
}

DEFAULT_PAGE_SEO = {
    "home": {
        "title": "سفارش آنلاین تاج گل، پک ترحیم و حلوا خرما (ارسال فوری)",
        "description": "مجلس یار؛ مرجع خدمات مجالس ترحیم و تولد. سفارش آنلاین حلوا خرما، پک میوه، فینگر فود و تاج گل با پایین‌ترین قیمت و ارسال فوری. برای تضمین کیفیت، بخشی از وجه را هنگام تحویل بپردازید!",
        "keywords": [
            "حلوا",
            "خرما",
            "حلوا و خرما",
            "پک ترحیم",
            "گل مراسم",
            "گل ترحیم",
            "سفارش حلوا",
            "سفارش خرما",
            "پذیرایی ترحیم",
        ],
    },
    "shop": {
        "title": "فروشگاه حلوا، ترحیم و گل مراسم",
        "description": "خرید و سفارش انواع حلوا، پک ترحیم، گل مراسم و دیگر محصولات پذیرایی با بهترین کیفیت و تحویل سریع در تهران و البرز.",
        "keywords": [
            "حلوا",
            "پک ترحیم",
            "گل مراسم",
            "گل ترحیم",
            "سفارش حلوا",
            "پذیرایی ترحیم",
        ],
    },
    "builder": {
        "title": "ساخت پک اختصاصی",
        "description": "ساخت پک پذیرایی سفارشی با انتخاب بسته‌بندی، میوه، نوشیدنی و اسنک دلخواه",
        "keywords": ["ساخت پک", "پک اختصاصی", "پک سفارشی", "پذیرایی سفارشی"],
    },
    "about": {
        "title": "درباره ما",
        "description": "مجلس‌یار با هدف ارائه خدمات کامل و باکیفیت برای انواع مراسم و مجالس راه‌اندازی شده است.",
        "keywords": ["درباره مجلس یار", "خدمات مجالس", "پذیرایی مراسم"],
    },
    "contact": {
        "title": "تماس با ما",
        "description": "تماس با مجلس یار برای سفارش پک‌های پذیرایی. تماس تلفنی، واتساپ و اینستاگرام.",
        "keywords": ["تماس", "سفارش", "مجلس یار", "شماره تماس", "واتساپ"],
    },
    "cart": {
        "title": "سبد خرید",
        "description": "مشاهده و مدیریت سبد خرید پک‌های پذیرایی",
        "keywords": ["سبد خرید", "سفارش آنلاین", "پک پذیرایی"],
    },
    "checkout": {
        "title": "تکمیل سفارش",
        "description": "تکمیل اطلاعات و ثبت سفارش پک‌های پذیرایی",
        "keywords": ["تکمیل سفارش", "ثبت سفارش", "پذیرایی مراسم"],
    },
    "track": {
        "title": "پیگیری سفارش",
        "description": "پیگیری وضعیت سفارش پک‌های پذیرایی با کد سفارش",
        "keywords": ["پیگیری سفارش", "کد سفارش", "وضعیت سفارش"],
    },
    "order": {
        "title": "جزئیات سفارش",
        "description": "مشاهده جزئیات و وضعیت سفارش",
        "keywords": ["جزئیات سفارش", "وضعیت سفارش", "سفارش مجلس یار"],
    },
}

DEFAULT_EVENT_PAGES = [
    {
        "id": "conference",
        "name": "فینگر فود",
        "slug": "conference",
        "description": "سفارش فینگر فود مراسم، همایش و پذیرایی شرکتی با چیدمان حرفه‌ای و آماده‌سازی سفارشی.",
        "seo_title": "سفارش فینگر فود و مزه برای تولد و جشن | تنوع مزه جذاب | مجلس یار",
        "seo_description": "سفارش فینگر فود، سینی مزه و ساندویچ سرد برای تولد و جشن‌ها. منوی متنوع با پایین‌ترین قیمت و ارسال فوری تهران، البرز. تضمین کیفیت و طعم عالی با امکان پرداخت بخشی از وجه زمان تحویل.",
        "seo_keywords": [
            "فینگر فود",
            "فینگرفود",
            "فینگر فود همایش",
            "فینگر فود مراسم",
            "فینگر فود شرکتی",
            "سفارش فینگر فود",
            "فینگرفود تهران",
        ],
        "faqs": [
            {
                "question": "فینگر فود برای چه مراسمی مناسب است؟",
                "answer": "فینگر فود برای همایش، جلسات شرکتی، افتتاحیه، دورهمی رسمی و پذیرایی ایستاده گزینه مناسبی است.",
            },
            {
                "question": "آیا امکان سفارش عمده فینگر فود وجود دارد؟",
                "answer": "بله، سفارش عمده فینگر فود برای مراسم با تعداد بالا انجام می‌شود و جزئیات بر اساس نوع پذیرایی هماهنگ می‌گردد.",
            },
        ],
        "icon": "🍢",
        "color": "bg-secondary",
        "available": True,
    },
    {
        "id": "memorial",
        "name": "ترحیم",
        "slug": "memorial",
        "description": "سفارش پک ترحیم، حلوا و اقلام پذیرایی مراسم با بسته‌بندی محترمانه و تحویل سریع در تهران و البرز.",
        "seo_title": "پک میوه، سینی میوه و پک ترحیم | قیمت رقابتی | مجلس یار",
        "seo_description": "فروش انواع پک میوه ترحیم و سینی میوه مجلسی با میوه‌های دست‌چین و شسته شده. ارزان‌ترین قیمت بازار و ارسال فوری. پرداخت در محل جهت اطمینان شما از کیفیت میوه‌ها.",
        "seo_keywords": [
            "حلوا",
            "سینی حلوا",
            "حلوا ترحیم",
            "پک ترحیم",
            "پذیرایی ترحیم",
            "پک ختم",
            "سفارش حلوا مراسم",
            "سفارش پک ترحیم",
            "خرما و حلوا",
        ],
        "faqs": [
            {
                "question": "آیا امکان سفارش حلوا برای مراسم ترحیم وجود دارد؟",
                "answer": "بله، سفارش حلوا و سینی حلوا برای مراسم ترحیم و یادبود انجام می‌شود و بسته به نوع مراسم امکان هماهنگی تعداد و نحوه ارائه وجود دارد.",
            },
            {
                "question": "پک ترحیم شامل چه اقلامی است؟",
                "answer": "بسته به محصول انتخابی، پک ترحیم می‌تواند شامل حلوا، خرما، نوشیدنی، دستمال و سایر اقلام پذیرایی مراسم باشد.",
            },
            {
                "question": "سفارش عمده پک ترحیم و حلوا چطور ثبت می‌شود؟",
                "answer": "برای سفارش عمده حلوا و پک ترحیم کافی است تعداد، زمان مراسم و محل تحویل را مشخص کنید تا هماهنگی نهایی انجام شود.",
            },
        ],
        "icon": "🕯️",
        "color": "bg-muted",
        "available": True,
    },
    {
        "id": "halva-khorma",
        "name": "حلوا و خرما",
        "slug": "halva-khorma",
        "description": "سفارش حلوا و خرما برای مراسم ترحیم، ختم، یادبود و پذیرایی رسمی با بسته‌بندی مرتب و تحویل سریع.",
        "seo_title": "خرما گردو و حلوا خرما مراسم ترحیم | انواع حلوا مجلسی | مجلس یار",
        "seo_description": "خرید آنلاین خرما گردو و حلوا خرما تازه برای مراسم ترحیم. انواع حلوا خرما شیک با تزیین حرفه‌ای و ارسال فوری تهران، البرز. تضمین کیفیت واقعی: بخشی از هزینه را پس از تحویل پرداخت کنید.",
        "seo_keywords": [
            "حلوا و خرما",
            "سفارش حلوا و خرما",
            "حلوا ترحیم",
            "خرما ترحیم",
            "حلوا مجلسی",
            "حلوا ختم",
            "خرما بسته بندی",
            "پک حلوا و خرما",
        ],
        "faqs": [
            {
                "question": "حلوا و خرما برای چه مراسمی مناسب است؟",
                "answer": "این بخش برای مراسم ترحیم، ختم، یادبود و پذیرایی‌های رسمی طراحی شده است و امکان سفارش عددی و عمده دارد.",
            },
            {
                "question": "آیا امکان سفارش حلوا و خرما با هم وجود دارد؟",
                "answer": "بله، بسته به نوع مراسم می‌توان حلوا و خرما را به‌صورت همزمان و در قالب پک‌های پذیرایی سفارش داد.",
            },
        ],
        "icon": "🍯",
        "color": "bg-accent",
        "available": True,
    },
    {
        "id": "party",
        "name": "گل",
        "slug": "party",
        "description": "سفارش گل و گل‌آرایی برای مراسم، ترحیم، هدیه و مناسبت‌های ویژه با طراحی آماده و اختصاصی.",
        "seo_title": "تاج گل ترحیم و ختم | گل تسلیت با ارسال فوری و تضمین کیفیت | مجلس یار",
        "seo_description": "سفارش تاج گل ترحیم و گل تسلیت با گل‌های تازه و قیمت رقابتی. ارسال فوری گل ختم به مساجد و تالارها. تنها در مجلس یار: تسویه بخشی از مبلغ، پس از رویت و تحویل گل!",
        "seo_keywords": [
            "گل مراسم",
            "گل ترحیم",
            "سفارش گل ترحیم",
            "گل آرایی",
            "گل‌آرایی",
            "دسته گل",
            "دسته گل ترحیم",
            "سفارش گل",
            "گل مناسب مراسم",
        ],
        "faqs": [
            {
                "question": "آیا امکان سفارش دسته گل با طرح مشابه تصاویر وجود دارد؟",
                "answer": "بله، سفارش دسته گل و گل‌آرایی بر اساس تصاویر نمونه یا با هماهنگی برای طراحی مشابه انجام می‌شود.",
            },
            {
                "question": "گل‌های این بخش برای چه مناسبت‌هایی مناسب هستند؟",
                "answer": "این محصولات برای ترحیم، هدیه، مجالس رسمی و سایر مناسبت‌های خاص قابل سفارش هستند.",
            },
            {
                "question": "آیا امکان سفارش گل برای مراسم ترحیم وجود دارد؟",
                "answer": "بله، سفارش گل ترحیم و دسته گل مناسب مراسم یادبود با هماهنگی نوع چیدمان و سبک موردنظر انجام می‌شود.",
            },
        ],
        "icon": "💐",
        "color": "bg-primary/20",
        "available": True,
    },
]


def default_site_top_notice() -> dict:
    return deepcopy(DEFAULT_SITE_TOP_NOTICE)


def default_homepage_benefits_section() -> dict:
    return deepcopy(DEFAULT_HOMEPAGE_BENEFITS_SECTION)


def default_site_branding() -> dict:
    return deepcopy(DEFAULT_SITE_BRANDING)


def default_theme_palette() -> dict:
    return deepcopy(DEFAULT_THEME_PALETTE)


def default_page_seo() -> dict:
    return deepcopy(DEFAULT_PAGE_SEO)


def default_event_pages() -> list[dict]:
    return deepcopy(DEFAULT_EVENT_PAGES)


def _normalize_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_bool(value, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _normalize_text_list(value, default: list[str] | None = None) -> list[str]:
    if not isinstance(value, list):
        value = default or []

    normalized: list[str] = []
    for item in value:
        text = _normalize_text(item)
        if text:
            normalized.append(text)
    return normalized


def _normalize_hex(value, fallback: str) -> str:
    text = _normalize_text(value).lstrip("#")
    if len(text) == 3:
        text = "".join(ch * 2 for ch in text)
    if len(text) != 6:
        return fallback
    if any(ch not in "0123456789abcdefABCDEF" for ch in text):
        return fallback
    return f"#{text.upper()}"


def normalize_site_top_notice(value) -> dict:
    payload = value if isinstance(value, dict) else {}
    return {
        "title": _normalize_text(payload.get("title", DEFAULT_SITE_TOP_NOTICE["title"])),
        "message": _normalize_text(payload.get("message", DEFAULT_SITE_TOP_NOTICE["message"])),
        "badge": _normalize_text(payload.get("badge", DEFAULT_SITE_TOP_NOTICE["badge"])),
    }


def normalize_homepage_benefits_section(value) -> dict:
    payload = value if isinstance(value, dict) else {}
    default_items = DEFAULT_HOMEPAGE_BENEFITS_SECTION["items"]
    raw_items = payload.get("items", default_items)
    if not isinstance(raw_items, list):
        raw_items = default_items

    normalized_items: list[dict[str, str]] = []
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            continue
        title = _normalize_text(raw_item.get("title"))
        description = _normalize_text(raw_item.get("description"))
        note = _normalize_text(raw_item.get("note"))
        if not title and not description and not note:
            continue
        normalized_items.append(
            {
                "title": title,
                "description": description,
                "note": note,
            }
        )

    return {
        "eyebrow": _normalize_text(payload.get("eyebrow", DEFAULT_HOMEPAGE_BENEFITS_SECTION["eyebrow"])),
        "title": _normalize_text(payload.get("title", DEFAULT_HOMEPAGE_BENEFITS_SECTION["title"])),
        "items": normalized_items,
    }


def normalize_site_branding(value) -> dict:
    payload = value if isinstance(value, dict) else {}
    defaults = DEFAULT_SITE_BRANDING
    return {
        "site_name": _normalize_text(payload.get("site_name", defaults["site_name"])),
        "site_alternate_name": _normalize_text(
            payload.get("site_alternate_name", defaults["site_alternate_name"])
        ),
        "site_tagline": _normalize_text(payload.get("site_tagline", defaults["site_tagline"])),
        "logo_alt": _normalize_text(payload.get("logo_alt", defaults["logo_alt"])),
        "meta_author": _normalize_text(payload.get("meta_author", defaults["meta_author"])),
        "default_meta_title": _normalize_text(
            payload.get("default_meta_title", defaults["default_meta_title"])
        ),
        "default_meta_description": _normalize_text(
            payload.get("default_meta_description", defaults["default_meta_description"])
        ),
        "default_meta_keywords": _normalize_text_list(
            payload.get("default_meta_keywords"),
            defaults["default_meta_keywords"],
        ),
        "admin_site_title": _normalize_text(payload.get("admin_site_title", defaults["admin_site_title"])),
        "admin_site_header": _normalize_text(
            payload.get("admin_site_header", defaults["admin_site_header"])
        ),
        "admin_site_subheader": _normalize_text(
            payload.get("admin_site_subheader", defaults["admin_site_subheader"])
        ),
        "admin_site_symbol": _normalize_text(
            payload.get("admin_site_symbol", defaults["admin_site_symbol"])
        ),
    }


def normalize_theme_palette(value) -> dict:
    payload = value if isinstance(value, dict) else {}
    defaults = DEFAULT_THEME_PALETTE
    return {
        "primary": _normalize_hex(payload.get("primary"), defaults["primary"]),
        "accent": _normalize_hex(payload.get("accent"), defaults["accent"]),
        "background": _normalize_hex(payload.get("background"), defaults["background"]),
        "surface": _normalize_hex(payload.get("surface"), defaults["surface"]),
        "foreground": _normalize_hex(payload.get("foreground"), defaults["foreground"]),
        "muted_foreground": _normalize_hex(
            payload.get("muted_foreground"),
            defaults["muted_foreground"],
        ),
        "success": _normalize_hex(payload.get("success"), defaults["success"]),
        "warning": _normalize_hex(payload.get("warning"), defaults["warning"]),
    }


def normalize_page_seo(value) -> dict:
    payload = value if isinstance(value, dict) else {}
    normalized: dict[str, dict[str, list[str] | str]] = {}
    page_keys = list(dict.fromkeys([*DEFAULT_PAGE_SEO.keys(), *payload.keys()]))

    for page_key in page_keys:
        default_entry = DEFAULT_PAGE_SEO.get(page_key, {"title": "", "description": "", "keywords": []})
        entry = payload.get(page_key, default_entry)
        if not isinstance(entry, dict):
            entry = default_entry
        normalized[page_key] = {
            "title": _normalize_text(entry.get("title", default_entry.get("title", ""))),
            "description": _normalize_text(
                entry.get("description", default_entry.get("description", ""))
            ),
            "keywords": _normalize_text_list(
                entry.get("keywords"),
                list(default_entry.get("keywords", [])),
            ),
        }

    return normalized


def normalize_event_pages(value) -> list[dict]:
    raw_pages = value if isinstance(value, list) else DEFAULT_EVENT_PAGES
    normalized_pages: list[dict] = []

    for index, raw_page in enumerate(raw_pages):
        if not isinstance(raw_page, dict):
            continue

        default_entry = DEFAULT_EVENT_PAGES[index] if index < len(DEFAULT_EVENT_PAGES) else {}
        page_id = _normalize_text(raw_page.get("id", default_entry.get("id", "")))
        slug = _normalize_text(raw_page.get("slug", default_entry.get("slug", page_id)))
        name = _normalize_text(raw_page.get("name", default_entry.get("name", "")))

        if not slug or not name:
            continue

        faq_defaults = default_entry.get("faqs", []) if isinstance(default_entry.get("faqs"), list) else []
        raw_faqs = raw_page.get("faqs", faq_defaults)
        if not isinstance(raw_faqs, list):
            raw_faqs = faq_defaults

        normalized_faqs: list[dict[str, str]] = []
        for raw_faq in raw_faqs:
            if not isinstance(raw_faq, dict):
                continue
            question = _normalize_text(raw_faq.get("question"))
            answer = _normalize_text(raw_faq.get("answer"))
            if not question and not answer:
                continue
            normalized_faqs.append(
                {
                    "question": question,
                    "answer": answer,
                }
            )

        normalized_pages.append(
            {
                "id": page_id or slug,
                "name": name,
                "slug": slug,
                "description": _normalize_text(
                    raw_page.get("description", default_entry.get("description", ""))
                ),
                "seo_title": _normalize_text(
                    raw_page.get("seo_title", default_entry.get("seo_title", name))
                ),
                "seo_description": _normalize_text(
                    raw_page.get("seo_description", default_entry.get("seo_description", ""))
                ),
                "seo_keywords": _normalize_text_list(
                    raw_page.get("seo_keywords"),
                    list(default_entry.get("seo_keywords", [])),
                ),
                "faqs": normalized_faqs,
                "icon": _normalize_text(raw_page.get("icon", default_entry.get("icon", "📦"))),
                "color": _normalize_text(raw_page.get("color", default_entry.get("color", "bg-muted"))),
                "available": _normalize_bool(
                    raw_page.get("available"),
                    bool(default_entry.get("available", True)),
                ),
            }
        )

    return normalized_pages


class SiteSetting(models.Model):
    """
    Single-record model for global storefront settings.
    Always stored with primary key 1.
    """

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    min_order_qty = models.PositiveIntegerField(default=40, validators=[MinValueValidator(1)])
    lead_time_hours = models.PositiveIntegerField(default=48, validators=[MinValueValidator(0)])
    allowed_provinces = models.JSONField(default=list, blank=True)
    delivery_windows = models.JSONField(default=list, blank=True)
    payment_methods = models.JSONField(default=list, blank=True)
    contact_phone = models.CharField(max_length=32, default="+989915505141", blank=True)
    contact_address = models.TextField(
        default="تهران، امیرآباد، خیابان کارگر شمالی، خیابان فرشی مقدم(شانزدهم)، پلاک ۹۱، واحد۶.",
        blank=True,
    )
    working_hours = models.CharField(
        max_length=255,
        default="شنبه تا پنجشنبه ۹ صبح تا ۹ شب",
        blank=True,
    )
    instagram_url = models.URLField(max_length=500, default="https://instagram.com/majlesyar", blank=True)
    telegram_url = models.URLField(max_length=500, default="https://t.me/majlesyar", blank=True)
    whatsapp_url = models.URLField(max_length=500, default="https://wa.me/989915505141", blank=True)
    bale_url = models.URLField(max_length=500, default="https://ble.ir/majlesyar", blank=True)
    maps_url = models.URLField(max_length=500, default="https://maps.google.com/?q=Tehran,Valiasr", blank=True)
    maps_embed_url = models.URLField(
        max_length=1000,
        default="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3239.9627430068!2d51.4066!3d35.7219!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x0%3A0x0!2zMzXCsDQzJzE4LjgiTiA1McKwMjQnMjMuOCJF!5e0!3m2!1sen!2s!4v1699999999999!5m2!1sen!2s",
        blank=True,
    )
    site_logo = models.ImageField(
        upload_to="site-settings/",
        blank=True,
        null=True,
        validators=[image_extension_validator],
        verbose_name="لوگوی سایت",
        help_text="لوگوی اصلی سایت برای هدر، فوتر و پنل مدیریت.",
    )
    site_favicon = models.ImageField(
        upload_to="site-settings/",
        blank=True,
        null=True,
        validators=[image_extension_validator],
        verbose_name="فاوآیکن سایت",
        help_text="آیکن مرورگر و تب سایت. ترجیحاً فایل مربعی و سبک بارگذاری شود.",
    )
    site_og_image = models.ImageField(
        upload_to="site-settings/",
        blank=True,
        null=True,
        validators=[image_extension_validator],
        verbose_name="تصویر اشتراک‌گذاری",
        help_text="تصویر پیش‌فرض شبکه‌های اجتماعی و Open Graph.",
    )
    site_branding = models.JSONField(
        default=default_site_branding,
        blank=True,
        help_text=(
            "ساختار پیشنهادی: "
            '{"site_name": "...", "site_alternate_name": "...", "site_tagline": "...", '
            '"logo_alt": "...", "meta_author": "...", "default_meta_title": "...", '
            '"default_meta_description": "...", "default_meta_keywords": ["..."], '
            '"admin_site_title": "...", "admin_site_header": "...", '
            '"admin_site_subheader": "...", "admin_site_symbol": "..."}'
        ),
    )
    theme_palette = models.JSONField(
        default=default_theme_palette,
        blank=True,
        help_text=(
            "ساختار پیشنهادی: "
            '{"primary": "#0C9FC7", "accent": "#D6A45B", "background": "#FDFBF7", '
            '"surface": "#FFFFFF", "foreground": "#24303A", '
            '"muted_foreground": "#5E6B78", "success": "#218A52", "warning": "#C98A10"}'
        ),
    )
    page_seo = models.JSONField(
        default=default_page_seo,
        blank=True,
        help_text=(
            "ساختار پیشنهادی: "
            '{"home": {"title": "...", "description": "...", "keywords": ["..."]}, '
            '"shop": {"title": "...", "description": "...", "keywords": ["..."]}}'
        ),
    )
    event_pages = models.JSONField(
        default=default_event_pages,
        blank=True,
        help_text=(
            "ساختار پیشنهادی: "
            '[{"id": "conference", "name": "...", "slug": "...", "description": "...", '
            '"seo_title": "...", "seo_description": "...", "seo_keywords": ["..."], '
            '"faqs": [{"question": "...", "answer": "..."}], '
            '"icon": "🍢", "color": "bg-secondary", "available": true}]'
        ),
    )
    site_top_notice = models.JSONField(
        default=default_site_top_notice,
        blank=True,
        help_text='ساختار پیشنهادی: {"title": "...", "message": "...", "badge": "..."}',
    )
    homepage_benefits_section = models.JSONField(
        default=default_homepage_benefits_section,
        blank=True,
        help_text=(
            "ساختار پیشنهادی: "
            '{"eyebrow": "...", "title": "...", "items": [{"title": "...", "description": "...", "note": "..."}]}'
        ),
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "تنظیمات سایت"
        verbose_name_plural = "تنظیمات سایت"

    def save(self, *args, **kwargs):
        self.pk = 1
        self.site_branding = normalize_site_branding(self.site_branding)
        self.theme_palette = normalize_theme_palette(self.theme_palette)
        self.page_seo = normalize_page_seo(self.page_seo)
        self.event_pages = normalize_event_pages(self.event_pages)
        self.site_top_notice = normalize_site_top_notice(self.site_top_notice)
        self.homepage_benefits_section = normalize_homepage_benefits_section(
            self.homepage_benefits_section
        )
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> "SiteSetting":
        instance, _ = cls.objects.get_or_create(pk=1)
        return instance

    def __str__(self) -> str:
        return "تنظیمات سراسری سایت"
