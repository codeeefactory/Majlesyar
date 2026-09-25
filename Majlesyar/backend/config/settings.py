from datetime import timedelta
import mimetypes
import os
from pathlib import Path
import re

from django.core.exceptions import ImproperlyConfigured
from django.templatetags.static import static as static_url

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIST_DIR = BASE_DIR / "frontend_dist"
VITE_ASSET_IMMUTABLE_RE = re.compile(r"^/static/assets/.+-[A-Za-z0-9_-]{8,}\.[A-Za-z0-9]+$")

mimetypes.add_type("image/avif", ".avif", strict=True)
mimetypes.add_type("image/webp", ".webp", strict=True)
mimetypes.add_type("image/jpeg", ".jpg", strict=True)
mimetypes.add_type("image/jpeg", ".jpeg", strict=True)


def is_vite_immutable_file(path: str, url: str) -> bool:
    return bool(VITE_ASSET_IMMUTABLE_RE.match(url))


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def env_int_list(name: str, default: str = "") -> list[int]:
    values: list[int] = []
    for item in env_list(name, default):
        try:
            values.append(int(item))
        except ValueError:
            continue
    return values


def admin_overrides_stylesheet(_request) -> str:
    return f"{static_url('admin/css/persian-admin-overrides.css')}?v=20260707-admin-comfort-theme2"


def admin_overrides_script(_request) -> str:
    return f"{static_url('admin/js/persian-admin-effects.js')}?v=20260707-time-dark"


DEFAULT_SECRET_KEY = "dev-insecure-secret-key-change-me"


def is_insecure_secret_key(value: str) -> bool:
    return value == DEFAULT_SECRET_KEY or value.startswith("django-insecure-")


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", DEFAULT_SECRET_KEY)
DEBUG = env_bool("DJANGO_DEBUG", True)
if not DEBUG and is_insecure_secret_key(SECRET_KEY):
    raise ImproperlyConfigured("Set DJANGO_SECRET_KEY to a long random value before running with DJANGO_DEBUG=0.")

ALLOWED_HOSTS = env_list(
    "DJANGO_ALLOWED_HOSTS",
    "localhost,127.0.0.1,testserver,majlesyar.com,www.majlesyar.com",
)


INSTALLED_APPS = [
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "django_filters",
    "drf_spectacular",
    "blog",
    "catalog",
    "vision",
    "site_settings",
    "orders",
    "operations",
    "google_maps_scraper",
    "telegram_bot",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "config.middleware.SecurityHeadersMiddleware",
    "config.middleware.SensitivePathBlockMiddleware",
    "config.middleware.LoginRateLimitMiddleware",
    "config.middleware.LegacyViteAssetRedirectMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "config.middleware.StripCrawlerDirectivesMiddleware",
    "config.middleware.OptimizedMediaCacheMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "config.csrf.ProxyAwareCsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

template_dirs = [BASE_DIR / "templates"]
if FRONTEND_DIST_DIR.exists():
    template_dirs.append(FRONTEND_DIST_DIR)

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": template_dirs,
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

LOGIN_URL = "/majmanage/login/"
LOGIN_REDIRECT_URL = "/majmanage/"
LOGOUT_REDIRECT_URL = "/majmanage/login/"


if env_bool("USE_POSTGRES", False) or os.getenv("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB", "pakto"),
            "USER": os.getenv("POSTGRES_USER", "pakto"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", "pakto"),
            "HOST": os.getenv("POSTGRES_HOST", "localhost"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": Path(os.getenv("SQLITE_DB_PATH", str(BASE_DIR / "db.sqlite3"))),
        }
    }


AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


LANGUAGE_CODE = "fa"
LANGUAGES = [("fa", "فارسی")]
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True


STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [FRONTEND_DIST_DIR] if FRONTEND_DIST_DIR.exists() else []
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
WHITENOISE_IMMUTABLE_FILE_TEST = is_vite_immutable_file
MEDIA_URL = os.getenv("DJANGO_MEDIA_URL", "/media/")
MEDIA_ROOT = Path(os.getenv("DJANGO_MEDIA_ROOT", str(BASE_DIR / "media")))

# Optional exact-file cache invalidation after a product image changes in Django admin.
# Keep credentials only in the production environment file, never in source control.
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")
CLOUDFLARE_ZONE_ID = os.getenv("CLOUDFLARE_ZONE_ID", "")
CLOUDFLARE_PUBLIC_BASE_URL = os.getenv("CLOUDFLARE_PUBLIC_BASE_URL", "https://majlesyar.com")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.AllowAny",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
}

GOOGLE_MAPS_SCRAPER = {
    "BASE_URL": os.getenv("GOOGLE_MAPS_SCRAPER_BASE_URL", "http://127.0.0.1:8081").rstrip("/"),
    "API_KEY": os.getenv("GOOGLE_MAPS_SCRAPER_API_KEY", ""),
    "CONNECT_TIMEOUT": float(os.getenv("GOOGLE_MAPS_SCRAPER_CONNECT_TIMEOUT", "5")),
    "READ_TIMEOUT": float(os.getenv("GOOGLE_MAPS_SCRAPER_READ_TIMEOUT", "60")),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": False,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Majlesyar API",
    "DESCRIPTION": "Backend API for products, settings, and order workflows.",
    "VERSION": "1.0.0",
    "ENUM_NAME_OVERRIDES": {
        "OrderStatus": "config.schema.order_status_choices",
        "InvoiceStatus": "config.schema.invoice_status_choices",
        "SmsStatus": "config.schema.sms_status_choices",
        "TelegramUpdateStatus": "config.schema.telegram_update_status_choices",
        "TelegramAuditStatus": "config.schema.telegram_audit_status_choices",
        "BlogPostStatus": "config.schema.blog_post_status_choices",
    },
}

CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    (
        "http://localhost:8080,http://127.0.0.1:8080,"
        "http://localhost:5173,http://127.0.0.1:5173,"
        "https://majlesyar.com,https://www.majlesyar.com"
    ),
)
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS",
    (
        "http://localhost:8080,http://127.0.0.1:8080,"
        "http://localhost:5173,http://127.0.0.1:5173,"
        "https://packetop.runflare.run,https://*.runflare.run,"
        "https://majlesyar.com,https://www.majlesyar.com"
    ),
)

# Reverse-proxy aware security settings for hosted environments (e.g. Runflare).
USE_X_FORWARDED_HOST = env_bool("USE_X_FORWARDED_HOST", True)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", not DEBUG)
SECURE_REDIRECT_EXEMPT = [r"^api/v1/health/$"]
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "63072000" if not DEBUG else "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", not DEBUG)
SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", not DEBUG)
SECURE_CONTENT_TYPE_NOSNIFF = env_bool("SECURE_CONTENT_TYPE_NOSNIFF", True)
SECURE_REFERRER_POLICY = os.getenv("SECURE_REFERRER_POLICY", "same-origin")
X_FRAME_OPTIONS = os.getenv("X_FRAME_OPTIONS", "DENY")
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", not DEBUG)
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", not DEBUG)
CSRF_COOKIE_SAMESITE = os.getenv("CSRF_COOKIE_SAMESITE", "Lax")
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
SESSION_COOKIE_HTTPONLY = env_bool("SESSION_COOKIE_HTTPONLY", True)
CSRF_PROXY_ALLOW_MISSING_REFERER = env_bool("CSRF_PROXY_ALLOW_MISSING_REFERER", True)

CONTENT_SECURITY_POLICY = os.getenv(
    "CONTENT_SECURITY_POLICY",
    (
        "default-src 'self'; "
        "script-src 'self' https://static.cloudflareinsights.com; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob: https:; "
        "font-src 'self' data:; "
        "connect-src 'self' https://majlesyar.com https://www.majlesyar.com https://cloudflareinsights.com; "
        "frame-src https://www.google.com https://maps.google.com; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'; "
        "require-trusted-types-for 'script'; "
        "trusted-types default; "
        "upgrade-insecure-requests"
    ),
)
ADMIN_CONTENT_SECURITY_POLICY = os.getenv(
    "ADMIN_CONTENT_SECURITY_POLICY",
    (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob: https:; "
        "font-src 'self' data:; "
        "connect-src 'self' https://majlesyar.com https://www.majlesyar.com; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'; "
        "upgrade-insecure-requests"
    ),
)
PERMISSIONS_POLICY = os.getenv(
    "PERMISSIONS_POLICY",
    "accelerometer=(), autoplay=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()",
)

SENSITIVE_BLOCKED_PATHS = {
    "/.env",
    "/.git",
    "/.git/",
    "/.git/head",
    "/admin/",
    "/wp-admin/",
    "/phpinfo.php",
}
SENSITIVE_BLOCKED_PATH_GLOBS = (
    "/.git/*",
    "/.env*",
    "/backup*",
    "/db.*",
    "/config.*",
    "/logs",
    "/logs/*",
    "/*.sql",
    "/*.sqlite",
    "/*.sqlite3",
    "/*.bak",
    "/*.backup",
    "/*.old",
    "/*.map",
    "/assets/*.map",
    "/static/*.map",
    "/static/assets/*.map",
)
LOGIN_RATE_LIMIT_PATHS = {
    "/majmanage/login/",
    "/api/v1/auth/token/",
}
LOGIN_RATE_LIMIT_ATTEMPTS = int(os.getenv("LOGIN_RATE_LIMIT_ATTEMPTS", "10"))
LOGIN_RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "300"))

PRIVATE_NOINDEX_PATHS = (
    "/checkout",
    "/dashboard",
    "/login",
    "/profile",
    "/signup",
    "/admin/login",
    "/admin/orders",
    "/admin/page-products",
)

# Django's built-in check only looks for the exact CsrfViewMiddleware path.
# We use a subclass that preserves CSRF protection while adding proxy-aware fallback logic.
SILENCED_SYSTEM_CHECKS = ["security.W003"]

UNFOLD = {
    "SITE_TITLE": "config.admin_branding.get_admin_site_title",
    "SITE_HEADER": "config.admin_branding.get_admin_site_header",
    "SITE_SUBHEADER": "config.admin_branding.get_admin_site_subheader",
    "SITE_SYMBOL": "config.admin_branding.get_admin_site_symbol",
    "SITE_LOGO": "config.admin_branding.get_admin_site_logo",
    "SITE_ICON": "config.admin_branding.get_admin_site_icon",
    "SITE_FAVICONS": "config.admin_branding.get_admin_site_favicons",
    "THEME": "light",
    "BORDER_RADIUS": "0.75rem",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": False,
    "STYLES": [
        admin_overrides_stylesheet,
    ],
    "SCRIPTS": [
        admin_overrides_script,
    ],
    "COLORS": "config.admin_branding.get_admin_colors",
}

VISION_ENABLED = env_bool("VISION_ENABLED", True)
VISION_MODEL_PATH = os.getenv("VISION_MODEL_PATH", str(BASE_DIR / "models" / "product_classifier.pt"))
VISION_CONFIDENCE_THRESHOLD = float(os.getenv("VISION_CONFIDENCE_THRESHOLD", "0.72"))
VISION_TOP_K = int(os.getenv("VISION_TOP_K", "3"))
VISION_DEVICE = os.getenv("VISION_DEVICE", "auto")
VISION_MAX_PIXELS = int(os.getenv("VISION_MAX_PIXELS", "16000000"))
VISION_MAX_DIMENSION = int(os.getenv("VISION_MAX_DIMENSION", "1600"))
VISION_ZERO_SHOT_ENABLED = env_bool("VISION_ZERO_SHOT_ENABLED", True)
VISION_ZERO_SHOT_MODEL = os.getenv("VISION_ZERO_SHOT_MODEL", "ViT-B-32")
VISION_ZERO_SHOT_PRETRAINED = os.getenv("VISION_ZERO_SHOT_PRETRAINED", "laion2b_s34b_b79k")
VISION_ZERO_SHOT_THRESHOLD = float(os.getenv("VISION_ZERO_SHOT_THRESHOLD", "0.08"))

# Private image-to-3D worker. GPU inference stays outside the web process.
PUBLIC_3D_MODELS_ENABLED = env_bool("PUBLIC_3D_MODELS_ENABLED", False)
PRODUCT_3D_GENERATOR_URL = os.getenv("PRODUCT_3D_GENERATOR_URL", "").strip()
PRODUCT_3D_GENERATOR_TOKEN = os.getenv("PRODUCT_3D_GENERATOR_TOKEN", "").strip()
PRODUCT_3D_GENERATOR_MODEL = os.getenv("PRODUCT_3D_GENERATOR_MODEL", "triposr").strip()
PRODUCT_3D_GENERATOR_TIMEOUT = int(os.getenv("PRODUCT_3D_GENERATOR_TIMEOUT", "180"))
PRODUCT_3D_MAX_BYTES = int(os.getenv("PRODUCT_3D_MAX_BYTES", str(25 * 1024 * 1024)))

# Optional GPU image-analysis endpoint. Empty means use the local classifier.
PRODUCT_IMAGE_ANALYZER_URL = os.getenv("PRODUCT_IMAGE_ANALYZER_URL", "").strip()
PRODUCT_IMAGE_ANALYZER_TIMEOUT = int(os.getenv("PRODUCT_IMAGE_ANALYZER_TIMEOUT", "180"))
ASSET_PROCESSING_MAX_ATTEMPTS = int(os.getenv("ASSET_PROCESSING_MAX_ATTEMPTS", "3"))
ASSET_PROCESSING_STALE_SECONDS = int(os.getenv("ASSET_PROCESSING_STALE_SECONDS", "1800"))

telegram_webhook_path = os.getenv("TELEGRAM_BOT_WEBHOOK_PATH", "api/v1/telegram/webhook/").strip()
telegram_webhook_path = telegram_webhook_path.strip("/")
if not telegram_webhook_path:
    telegram_webhook_path = "api/v1/telegram/webhook"
telegram_webhook_path = f"{telegram_webhook_path}/"

TELEGRAM_BOT = {
    "ENABLED": env_bool("TELEGRAM_BOT_ENABLED", False),
    "TOKEN": os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
    "USE_WEBHOOK": env_bool("TELEGRAM_BOT_USE_WEBHOOK", True),
    "WEBHOOK_SECRET": os.getenv("TELEGRAM_BOT_WEBHOOK_SECRET", "").strip(),
    "WEBHOOK_PATH": telegram_webhook_path,
    "BASE_URL": os.getenv("TELEGRAM_BOT_BASE_URL", "").strip().rstrip("/"),
    "ALLOWED_USER_IDS": env_int_list("TELEGRAM_BOT_ALLOWED_USER_IDS"),
    "ALLOWED_CHAT_IDS": env_int_list("TELEGRAM_BOT_ALLOWED_CHAT_IDS"),
    "ADMIN_ONLY": env_bool("TELEGRAM_BOT_ADMIN_ONLY", True),
    "NOTIFICATIONS_ENABLED": env_bool("TELEGRAM_BOT_NOTIFICATIONS_ENABLED", False),
    "CONFIRMATION_TTL_SECONDS": int(os.getenv("TELEGRAM_BOT_CONFIRMATION_TTL_SECONDS", "600")),
    "RATE_LIMIT_PER_MINUTE": int(os.getenv("TELEGRAM_BOT_RATE_LIMIT_PER_MINUTE", "30")),
}

KAVENEGAR_API_KEY = os.getenv("KAVENEGAR_API_KEY", "").strip()
KAVENEGAR_SENDER = os.getenv("KAVENEGAR_SENDER", "").strip()
MAJLESYAR_DESKTOP_UI_TEST_MODE = os.getenv("MAJLESYAR_DESKTOP_UI_TEST_MODE", "").strip().lower() in {"1", "true", "yes", "on"}
