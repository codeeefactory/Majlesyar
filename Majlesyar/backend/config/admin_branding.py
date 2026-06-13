from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import dataclass

from django.db.utils import OperationalError, ProgrammingError
from django.templatetags.static import static as static_url


PERSIAN_DIGIT_TRANS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

EVENT_THEME_PRESETS = {
    "conference": {
        "name": "فینگر فود",
        "icon": "🍢",
        "accent": "#D67641",
        "secondary": "#7FB780",
        "note": "ریتم سریع، چیدمان تمیز و پذیرایی جمع‌وجور",
    },
    "memorial": {
        "name": "ترحیم",
        "icon": "🕯️",
        "accent": "#71808F",
        "secondary": "#B1BAC3",
        "note": "وقار، آرامش بصری و دقت در جزئیات سفارش",
    },
    "halva-khorma": {
        "name": "حلوا و خرما",
        "icon": "🍯",
        "accent": "#C98E34",
        "secondary": "#8A5A2B",
        "note": "گرمای سنتی، بافت غنی و حس اصیل مراسم",
    },
    "party": {
        "name": "گل",
        "icon": "💐",
        "accent": "#C35F78",
        "secondary": "#5FA37B",
        "note": "لطافت گل‌آرایی، رنگ زنده و حال‌وهوای مراسم‌محور",
    },
}


@dataclass(frozen=True)
class FallbackAdminConfig:
    branding: dict
    palette: dict


def _get_fallback_config() -> FallbackAdminConfig:
    from site_settings.models import DEFAULT_SITE_BRANDING, DEFAULT_THEME_PALETTE

    return FallbackAdminConfig(
        branding=dict(DEFAULT_SITE_BRANDING),
        palette=dict(DEFAULT_THEME_PALETTE),
    )


def _load_site_setting(request=None):
    cache_attr = "_majlesyar_site_setting_cache"
    if request is not None and hasattr(request, cache_attr):
        return getattr(request, cache_attr)

    try:
        from site_settings.models import SiteSetting

        setting = SiteSetting.load()
    except (OperationalError, ProgrammingError):
        setting = None

    if request is not None:
        setattr(request, cache_attr, setting)
    return setting


def _get_branding(request=None) -> dict:
    fallback = _get_fallback_config().branding
    setting = _load_site_setting(request)
    if not setting:
        return fallback
    branding = setting.site_branding if isinstance(setting.site_branding, dict) else {}
    return {**fallback, **branding}


def _get_palette(request=None) -> dict:
    fallback = _get_fallback_config().palette
    setting = _load_site_setting(request)
    if not setting:
        return fallback
    palette = setting.theme_palette if isinstance(setting.theme_palette, dict) else {}
    return {**fallback, **palette}


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    normalized = str(value or "").strip().lstrip("#")
    if len(normalized) == 3:
        normalized = "".join(ch * 2 for ch in normalized)
    if len(normalized) != 6:
        return (0, 0, 0)
    try:
        return tuple(int(normalized[index : index + 2], 16) for index in (0, 2, 4))
    except ValueError:
        return (0, 0, 0)


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def _rgb_to_str(rgb: tuple[int, int, int]) -> str:
    return f"{rgb[0]} {rgb[1]} {rgb[2]}"


def _mix(base: str, overlay: str, ratio: float) -> str:
    ratio = max(0.0, min(1.0, ratio))
    base_rgb = _hex_to_rgb(base)
    overlay_rgb = _hex_to_rgb(overlay)
    mixed = tuple(
        round((base_channel * (1 - ratio)) + (overlay_channel * ratio))
        for base_channel, overlay_channel in zip(base_rgb, overlay_rgb)
    )
    return _rgb_to_hex(mixed)


def _scale(base: str, *, light_base: str = "#FFFFFF", dark_base: str = "#000000") -> dict[str, str]:
    return {
        "50": _mix(light_base, base, 0.08),
        "100": _mix(light_base, base, 0.14),
        "200": _mix(light_base, base, 0.22),
        "300": _mix(light_base, base, 0.34),
        "400": _mix(light_base, base, 0.52),
        "500": base,
        "600": _mix(base, dark_base, 0.12),
        "700": _mix(base, dark_base, 0.24),
        "800": _mix(base, dark_base, 0.36),
        "900": _mix(base, dark_base, 0.5),
        "950": _mix(base, dark_base, 0.66),
    }


def _fa_number(value: int) -> str:
    return str(value).translate(PERSIAN_DIGIT_TRANS)


def _join_fa(values: list[str]) -> str:
    cleaned = [str(value).strip() for value in values if str(value).strip()]
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0]
    if len(cleaned) == 2:
        return f"{cleaned[0]} و {cleaned[1]}"
    return f"{'، '.join(cleaned[:-1])} و {cleaned[-1]}"


def _normalize_event_slug(value: str | None) -> str:
    slug = str(value or "").strip()
    if slug == "defense":
        return "halva-khorma"
    return slug


def _get_event_pages(request=None) -> list[dict]:
    from site_settings.models import DEFAULT_EVENT_PAGES

    setting = _load_site_setting(request)
    raw_pages = setting.event_pages if setting and isinstance(setting.event_pages, list) else deepcopy(DEFAULT_EVENT_PAGES)
    pages: list[dict] = []
    for raw_page in raw_pages:
        if not isinstance(raw_page, dict):
            continue
        slug = _normalize_event_slug(raw_page.get("slug") or raw_page.get("id"))
        if not slug:
            continue
        preset = EVENT_THEME_PRESETS.get(slug, {})
        pages.append(
            {
                "id": raw_page.get("id") or slug,
                "slug": slug,
                "name": raw_page.get("name") or preset.get("name") or slug,
                "icon": raw_page.get("icon") or preset.get("icon") or "✦",
                "available": raw_page.get("available", True),
            }
        )

    available_pages = [page for page in pages if page.get("available", True)]
    return available_pages or pages


def _get_event_mix_counts() -> dict:
    try:
        from catalog.models import Product, normalize_event_types
    except Exception:
        return {
            "counts": Counter(),
            "available_counts": Counter(),
            "featured_counts": Counter(),
            "total_products": 0,
            "available_products": 0,
            "featured_products": 0,
        }

    try:
        rows = Product.objects.values_list("event_types", "available", "featured")
    except (OperationalError, ProgrammingError):
        return {
            "counts": Counter(),
            "available_counts": Counter(),
            "featured_counts": Counter(),
            "total_products": 0,
            "available_products": 0,
            "featured_products": 0,
        }

    counts: Counter[str] = Counter()
    available_counts: Counter[str] = Counter()
    featured_counts: Counter[str] = Counter()
    total_products = 0
    available_products = 0
    featured_products = 0

    for raw_event_types, is_available, is_featured in rows.iterator():
        total_products += 1
        if is_available:
            available_products += 1
        if is_featured:
            featured_products += 1

        normalized = normalize_event_types(raw_event_types if isinstance(raw_event_types, list) else [])
        for slug in dict.fromkeys(normalized):
            counts[slug] += 1
            if is_available:
                available_counts[slug] += 1
            if is_featured:
                featured_counts[slug] += 1

    return {
        "counts": counts,
        "available_counts": available_counts,
        "featured_counts": featured_counts,
        "total_products": total_products,
        "available_products": available_products,
        "featured_products": featured_products,
    }


def get_admin_theme_manifest(request=None) -> dict:
    cache_attr = "_majlesyar_admin_theme_manifest"
    if request is not None and hasattr(request, cache_attr):
        return getattr(request, cache_attr)

    palette = _get_palette(request)
    event_pages = _get_event_pages(request)
    mix_counts = _get_event_mix_counts()
    counts = mix_counts["counts"]
    available_counts = mix_counts["available_counts"]
    featured_counts = mix_counts["featured_counts"]

    events: list[dict] = []
    for index, page in enumerate(event_pages):
        slug = page["slug"]
        preset = EVENT_THEME_PRESETS.get(slug, {})
        accent = preset.get("accent") or palette["primary"]
        secondary = preset.get("secondary") or palette["accent"]
        soft = _mix(palette["background"], accent, 0.17)
        mist = _mix(palette["surface"], secondary, 0.16)
        deep = _mix(accent, palette["foreground"], 0.18)
        count = int(counts.get(slug, 0))
        available_count = int(available_counts.get(slug, 0))
        featured_count = int(featured_counts.get(slug, 0))
        accent_rgb = _rgb_to_str(_hex_to_rgb(accent))
        events.append(
            {
                "slug": slug,
                "name": page["name"],
                "icon": page["icon"],
                "note": preset.get("note") or "هویت این بخش از ترکیب محصولات واقعی شما می‌آید.",
                "count": count,
                "available_count": available_count,
                "featured_count": featured_count,
                "count_label": f"{_fa_number(count)} محصول" if count else "در حال تکمیل",
                "available_label": f"{_fa_number(available_count)} آماده سفارش" if available_count else "آماده چیدمان تازه",
                "featured_label": f"{_fa_number(featured_count)} ویژه" if featured_count else "",
                "is_active": count > 0,
                "style": (
                    f"--event-accent:{accent};"
                    f"--event-secondary:{secondary};"
                    f"--event-soft:{soft};"
                    f"--event-mist:{mist};"
                    f"--event-deep:{deep};"
                    f"--event-accent-rgb:{accent_rgb};"
                    f"--chip-delay:{index * 68}ms;"
                ),
            }
        )

    blend_colors = [EVENT_THEME_PRESETS.get(event["slug"], {}).get("accent") or palette["primary"] for event in events]
    if not blend_colors:
        blend_colors = [palette["primary"], palette["accent"]]
    while len(blend_colors) < 4:
        blend_colors.append(blend_colors[-1])

    active_names = [event["name"] for event in events if event["is_active"]] or [event["name"] for event in events]
    metrics = [
        {"label": "محصول", "value": _fa_number(mix_counts["total_products"])},
        {"label": "آماده", "value": _fa_number(mix_counts["available_products"])},
        {"label": "ویژه", "value": _fa_number(mix_counts["featured_products"])},
        {"label": "طیف فعال", "value": _fa_number(sum(1 for event in events if event["is_active"]) or len(events))},
    ]
    summary = {
        "title": "پنلی هم‌نفس با تمام طیف‌های محصولات مجلس‌یار",
        "description": (
            "رنگ، حرکت و بافت این داشبورد از ترکیب واقعی "
            f"{_join_fa(active_names)} الهام گرفته تا مدیریت سفارش‌ها نرم، سریع و متناسب با حال‌وهوای هر محصول باشد."
        ),
        "line": (
            f"{_join_fa(active_names)} در این پنل با یک طیف زنده کنار هم نشسته‌اند؛ "
            f"{_fa_number(mix_counts['total_products'])} محصول در این ترکیب دیده می‌شود."
        ),
    }
    manifest = {
        "events": events,
        "metrics": metrics,
        "summary": summary,
        "blend_style": (
            f"--admin-spectrum-a:{blend_colors[0]};"
            f"--admin-spectrum-b:{blend_colors[1]};"
            f"--admin-spectrum-c:{blend_colors[2]};"
            f"--admin-spectrum-d:{blend_colors[3]};"
            f"--admin-spectrum-surface:{palette['surface']};"
            f"--admin-spectrum-foreground:{palette['foreground']};"
        ),
    }
    if request is not None:
        setattr(request, cache_attr, manifest)
    return manifest


def get_admin_site_title(request) -> str:
    return _get_branding(request).get("admin_site_title") or "Ù¾Ù†Ù„ Ù…Ø¯ÛŒØ±ÛŒØª Ù…Ø¬Ù„Ø³ ÛŒØ§Ø±"


def get_admin_site_header(request) -> str:
    branding = _get_branding(request)
    return branding.get("admin_site_header") or branding.get("site_name") or "Ù…Ø¬Ù„Ø³ ÛŒØ§Ø±"


def get_admin_site_subheader(request) -> str:
    branding = _get_branding(request)
    return branding.get("admin_site_subheader") or branding.get("site_tagline") or ""


def get_admin_site_symbol(request) -> str:
    return _get_branding(request).get("admin_site_symbol") or "inventory_2"


def get_admin_site_logo(request):
    setting = _load_site_setting(request)
    if setting and setting.site_logo:
        return setting.site_logo.url
    return None


def get_admin_site_icon(request):
    setting = _load_site_setting(request)
    if setting and setting.site_favicon:
        return setting.site_favicon.url
    if setting and setting.site_logo:
        return setting.site_logo.url
    return None


def get_admin_site_favicons(request):
    setting = _load_site_setting(request)
    if setting and setting.site_favicon:
        favicon_url = setting.site_favicon.url
        return [
            {
                "href": favicon_url,
                "rel": "icon",
                "type": "image/png",
            },
            {
                "href": favicon_url,
                "rel": "apple-touch-icon",
            },
        ]

    default_favicon = static_url("favicon.ico")
    return [
        {
            "href": default_favicon,
            "rel": "icon",
            "type": "image/x-icon",
        }
    ]


def get_admin_colors(request):
    palette = _get_palette(request)
    background = palette["background"]
    surface = palette["surface"]
    foreground = palette["foreground"]
    muted = palette["muted_foreground"]
    primary = palette["primary"]
    accent = palette["accent"]

    return {
        "base": _scale(surface, light_base=background, dark_base=foreground),
        "primary": _scale(primary, light_base=background, dark_base=foreground),
        "accent": _scale(accent, light_base=background, dark_base=foreground),
        "font": {
            "subtle-light": muted,
            "subtle-dark": _mix("#FFFFFF", muted, 0.7),
            "default-light": foreground,
            "default-dark": _mix("#FFFFFF", foreground, 0.82),
            "important-light": _mix(foreground, "#000000", 0.08),
            "important-dark": "#FFFFFF",
        },
    }
