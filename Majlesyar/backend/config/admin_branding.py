from __future__ import annotations

from dataclasses import dataclass

from django.db.utils import OperationalError, ProgrammingError
from django.templatetags.static import static as static_url


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


def get_admin_site_title(request) -> str:
    return _get_branding(request).get("admin_site_title") or "پنل مدیریت مجلس یار"


def get_admin_site_header(request) -> str:
    branding = _get_branding(request)
    return branding.get("admin_site_header") or branding.get("site_name") or "مجلس یار"


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
