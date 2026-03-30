from datetime import timedelta
import os
from pathlib import Path
import re

from django.templatetags.static import static as static_url

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIST_DIR = BASE_DIR / "frontend_dist"
VITE_ASSET_IMMUTABLE_RE = re.compile(r"^/static/assets/.+-[A-Za-z0-9_-]{8,}\.[A-Za-z0-9]+$")


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


def admin_overrides_stylesheet(_request) -> str:
    return static_url("admin/css/persian-admin-overrides.css")


def admin_overrides_script(_request) -> str:
    return static_url("admin/js/persian-admin-effects.js")


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-insecure-secret-key-change-me")
DEBUG = env_bool("DJANGO_DEBUG", True)
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
    "catalog",
    "site_settings",
    "orders",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.gzip.GZipMiddleware",
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
            "NAME": BASE_DIR / "db.sqlite3",
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

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": False,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Majlesyar API",
    "DESCRIPTION": "Backend API for products, settings, and order workflows.",
    "VERSION": "1.0.0",
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
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", not DEBUG)
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", not DEBUG)
CSRF_PROXY_ALLOW_MISSING_REFERER = env_bool("CSRF_PROXY_ALLOW_MISSING_REFERER", True)

UNFOLD = {
    "SITE_TITLE": "پنل مدیریت مجلس یار",
    "SITE_HEADER": "مجلس یار",
    "SITE_SUBHEADER": "مدیریت فروش و سفارش پک‌های پذیرایی",
    "SITE_SYMBOL": "inventory_2",
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
    "COLORS": {
        "base": {
            "50": "#fdfbf7",
            "100": "#faf6ef",
            "200": "#f3ebdd",
            "300": "#e8dcc7",
            "400": "#d8c3a6",
            "500": "#c2a585",
            "600": "#9f8468",
            "700": "#7e6851",
            "800": "#5f4f3f",
            "900": "#463b31",
            "950": "#2f2620",
        },
        "primary": {
            "50": "#e6f9fd",
            "100": "#ccf3fb",
            "200": "#99e8f8",
            "300": "#66dcf4",
            "400": "#33d1f1",
            "500": "#00c2f2",
            "600": "#00a9d4",
            "700": "#0088aa",
            "800": "#006b85",
            "900": "#004f63",
            "950": "#003342",
        },
        "font": {
            "subtle-light": "#6a5a49",
            "subtle-dark": "#d8c3a6",
            "default-light": "#3c3128",
            "default-dark": "#f3ebdd",
            "important-light": "#241d17",
            "important-dark": "#faf6ef",
        },
    },
}
