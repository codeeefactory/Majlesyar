from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import unquote

from django.conf import settings
from django.db.utils import OperationalError, ProgrammingError
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.templatetags.static import static as static_url
from django.views.decorators.http import require_safe
from django.views.generic import TemplateView


def _read_file_text(paths: list[Path]) -> str | None:
    for path in paths:
        if path.exists() and path.is_file():
            return path.read_text(encoding="utf-8")
    return None


def _default_robots(sitemap_url: str) -> str:
    return "\n".join(
        [
            "# Robots.txt for Majlesyar",
            "User-agent: *",
            "Allow: /",
            "",
            f"Sitemap: {sitemap_url}",
            "",
        ]
    )


def _strip_unknown_robots_directives(content: str) -> str:
    sensitive_disallows = ("/admin", "/checkout", "/order")
    lines = [
        line
        for line in content.splitlines()
        if not line.lstrip().lower().startswith("content-signal:")
        and not (
            line.lstrip().lower().startswith("disallow:")
            and any(path in line.lstrip().lower() for path in sensitive_disallows)
        )
    ]
    return "\n".join(lines) + ("\n" if content.endswith("\n") else "")


def _uncached_text_response(content: str, content_type: str) -> HttpResponse:
    response = HttpResponse(content, content_type=content_type)
    response.headers["Cache-Control"] = "no-store, max-age=0, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


PRIVATE_SPA_PREFIXES = (
    "/checkout",
    "/dashboard",
    "/login",
    "/profile",
    "/signup",
    "/admin/login",
    "/admin/orders",
    "/admin/page-products",
)


STATIC_PUBLIC_PAGES = {
    "/": ("WebPage", "Home", "Majlesyar storefront home page."),
    "/about": ("AboutPage", "About Majlesyar", "About Majlesyar and its ceremony product services."),
    "/contact": ("ContactPage", "Contact Majlesyar", "Contact Majlesyar for ceremony product orders."),
    "/blog": ("Blog", "Majlesyar Blog", "Majlesyar articles and buying guides."),
    "/terms": ("WebPage", "Terms", "Majlesyar website terms and order rules."),
    "/builder": ("WebApplication", "Pack Builder", "Build a custom ceremony pack."),
    "/cart": ("WebPage", "Cart", "Majlesyar shopping cart."),
    "/track": ("WebPage", "Track Order", "Track Majlesyar order status."),
}

FORCED_NOT_FOUND_PATHS = frozenset(
    {
        "/pack/personal",
        "/pack/memorial/luxury",
        "/flower/funeral-bouquet",
        "/halva-khorma/luxury",
        "/food/charcuterie-board",
        "/food/juice",
    }
)


def _normalize_path(path: str) -> str:
    normalized = f"/{path.strip('/')}" if path.strip("/") else "/"
    return normalized.rstrip("/") or "/"


def _absolute_url(request, value: str | None) -> str | None:
    if not value:
        return None
    if value.startswith(("http://", "https://")):
        return value
    return request.build_absolute_uri(value)


def _jsonld_script(payload: dict) -> str:
    json_payload = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    json_payload = json_payload.replace("</", "<\\/")
    return f'<script type="application/ld+json" data-seo-server>{json_payload}</script>'


def _jsonld_scripts(payload: dict) -> str:
    context = payload.get("@context", "https://schema.org")
    graph = payload.get("@graph")
    if not isinstance(graph, list):
        return _jsonld_script(payload)

    scripts = []
    for item in graph:
        if not isinstance(item, dict):
            continue
        item_payload = {"@context": context, **item}
        scripts.append(_jsonld_script(item_payload))
    return "\n    ".join(scripts)


def _product_image_url(request, product) -> str | None:
    image_variants = product.image_variants or {}
    for variant_key in ("avif", "webp", "jpeg", "original"):
        variants = image_variants.get(variant_key)
        if isinstance(variants, dict):
            for size_key in ("1200", "960", "720", "480"):
                url = variants.get(size_key)
                if url:
                    return _absolute_url(request, str(url))
        elif isinstance(variants, str) and variants:
            return _absolute_url(request, variants)

    if product.image:
        return request.build_absolute_uri(product.image.url)
    return None


def _site_setting():
    try:
        from site_settings.models import SiteSetting

        return SiteSetting.load()
    except (OperationalError, ProgrammingError):
        return None


def _event_page_for_path(path: str, site_setting) -> dict | None:
    if not site_setting:
        return None
    normalized_path = _normalize_path(path)
    for page in site_setting.event_pages or []:
        if not isinstance(page, dict) or page.get("hidden"):
            continue
        route_path = _normalize_path(str(page.get("route_path") or f"/events/{page.get('slug', '')}"))
        if normalized_path == route_path:
            return page
    return None


def _page_seo_for_key(site_setting, key: str) -> dict:
    if not site_setting:
        return {}
    page_seo = getattr(site_setting, "page_seo", {}) or {}
    entry = page_seo.get(key)
    return entry if isinstance(entry, dict) else {}


def _product_for_path(path: str):
    normalized_path = _normalize_path(unquote(path))
    if normalized_path == "/" or normalized_path == "/product" or normalized_path.startswith("/product/"):
        return None

    try:
        from catalog.models import Product
    except (OperationalError, ProgrammingError):
        return None

    return Product.objects.filter(public_path=normalized_path).prefetch_related("categories").first()


def _temporary_product_for_path(path: str):
    product = _product_for_path(path)
    return product if product and product.is_temporary else None


def _blog_post_for_path(path: str):
    parts = [unquote(part) for part in path.strip("/").split("/") if part]
    if len(parts) != 2 or parts[0] != "blog":
        return None

    try:
        from blog.views import published_posts_queryset
    except (OperationalError, ProgrammingError):
        return None

    return published_posts_queryset().filter(slug=parts[1]).first()


def _is_home_path(path: str) -> bool:
    return _normalize_path(path) == "/"


def _base_structured_data(request, site_setting) -> list[dict]:
    base_url = request.build_absolute_uri("/").rstrip("/")
    branding = (getattr(site_setting, "site_branding", None) or {}) if site_setting else {}
    site_name = branding.get("site_name") or "مجلس یار"
    alternate_name = branding.get("site_alternate_name") or "Majlesyar"
    logo_url = None
    if site_setting and site_setting.site_logo:
        logo_url = request.build_absolute_uri(site_setting.site_logo.url)

    same_as = [
        getattr(site_setting, field, "")
        for field in ("instagram_url", "telegram_url", "whatsapp_url", "bale_url", "eitaa_url", "soroush_url", "rubika_url")
        if site_setting
    ]
    same_as = [url for url in same_as if url]
    contact_address = getattr(site_setting, "contact_address", "") if site_setting else ""

    business = {
        "@type": "LocalBusiness",
        "@id": f"{base_url}/#organization",
        "name": site_name,
        "alternateName": alternate_name,
        "url": base_url,
        "telephone": getattr(site_setting, "contact_phone", "") if site_setting else "",
        "contactPoint": {
            "@type": "ContactPoint",
            "telephone": getattr(site_setting, "contact_phone", "") if site_setting else "",
            "contactType": "customer service",
            "availableLanguage": "Persian",
        },
        "address": {
            "@type": "PostalAddress",
            "streetAddress": contact_address,
            "addressLocality": "تهران",
            "addressRegion": "تهران",
            "postalCode": "1439814383",
            "addressCountry": "IR",
        },
        "geo": {
            "@type": "GeoCoordinates",
            "latitude": "35.7219",
            "longitude": "51.4066",
        },
        "openingHours": getattr(site_setting, "working_hours", "") if site_setting else "",
        "areaServed": [
            {"@type": "AdministrativeArea", "name": "Tehran"},
            {"@type": "AdministrativeArea", "name": "Alborz"},
        ],
        "sameAs": same_as,
    }
    if logo_url:
        business["logo"] = logo_url
        business["image"] = logo_url

    website = {
        "@type": "WebSite",
        "@id": f"{base_url}/#website",
        "url": base_url,
        "name": site_name,
        "alternateName": alternate_name,
        "publisher": {"@id": f"{base_url}/#organization"},
        "inLanguage": "fa-IR",
    }

    graph = [website]
    if _is_home_path(request.path):
        graph.insert(0, business)
    return graph


def _breadcrumb_schema(base_url: str, items: list[tuple[str, str]]) -> dict:
    return {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": index,
                "name": name,
                "item": f"{base_url}{path}",
            }
            for index, (name, path) in enumerate(items, start=1)
        ],
    }


def _event_page_lookup(site_setting) -> tuple[dict[str, dict], dict[str, dict]]:
    pages = [
        page
        for page in (getattr(site_setting, "event_pages", None) or [])
        if isinstance(page, dict) and not page.get("hidden")
    ]
    by_slug = {str(page.get("slug") or "").strip(): page for page in pages if str(page.get("slug") or "").strip()}
    by_route = {
        _normalize_path(str(page.get("route_path") or f"/events/{page.get('slug', '')}")): page
        for page in pages
    }
    return by_slug, by_route


def _breadcrumb_items_for_route(site_setting, route_path: str, leaf_name: str | None = None, leaf_path: str | None = None) -> list[tuple[str, str]]:
    _by_slug, by_route = _event_page_lookup(site_setting)
    items = [("Majlesyar", "/")]
    parts = [part for part in _normalize_path(route_path).strip("/").split("/") if part]

    for index in range(len(parts)):
        current_path = "/" + "/".join(parts[: index + 1])
        page = by_route.get(current_path)
        if page:
            name = str(page.get("name") or page.get("seo_title") or parts[index])
        else:
            name = parts[index].replace("-", " ").replace("_", " ").title()
        items.append((name, current_path))

    if leaf_name and leaf_path:
        items.append((leaf_name, leaf_path))

    return items


def _product_collection_url(request, product, site_setting) -> str:
    by_slug, _by_route = _event_page_lookup(site_setting)
    for event_slug in product.event_types or []:
        page = by_slug.get(str(event_slug))
        if page:
            return _normalize_path(str(page.get("route_path") or f"/events/{event_slug}"))
    return "/pack"


def _event_products(event_page: dict) -> list:
    slug = str(event_page.get("slug") or event_page.get("id") or "").strip()
    if not slug:
        return []
    try:
        from catalog.models import PageProductPlacement
        from catalog.services import get_page_products

        _target, products, _uses_custom_order = get_page_products(PageProductPlacement.PageType.EVENT, slug)
    except (OperationalError, ProgrammingError, ValueError):
        return []
    return [product for product in products if not product.is_temporary]


def _static_page_structured_data(request, path: str, site_setting) -> list[dict]:
    normalized_path = _normalize_path(path)
    if normalized_path not in STATIC_PUBLIC_PAGES:
        return []

    schema_type, fallback_name, fallback_description = STATIC_PUBLIC_PAGES[normalized_path]
    base_url = request.build_absolute_uri("/").rstrip("/")
    page_url = f"{base_url}{'' if normalized_path == '/' else normalized_path}"
    seo_key = "home" if normalized_path == "/" else normalized_path.strip("/").split("/")[0]
    seo = _page_seo_for_key(site_setting, seo_key)
    name = str(seo.get("title") or fallback_name)
    description = str(seo.get("description") or fallback_description)

    graph = [
        {
            "@type": schema_type,
            "@id": f"{page_url}#webpage",
            "url": page_url,
            "name": name,
            "description": description,
            "isPartOf": {"@id": f"{base_url}/#website"},
            "publisher": {"@id": f"{base_url}/#organization"},
            "inLanguage": "fa-IR",
        }
    ]
    if normalized_path != "/":
        graph.append(_breadcrumb_schema(base_url, [("Majlesyar", "/"), (fallback_name, normalized_path)]))
    return graph


def _blog_post_structured_data(request, post) -> list[dict]:
    base_url = request.build_absolute_uri("/").rstrip("/")
    post_url = f"{base_url}/blog/{post.slug}"
    author_name = ""
    if post.author:
        author_name = post.author.get_full_name() or post.author.get_username()
    image_url = request.build_absolute_uri(post.hero_image.url) if post.hero_image else None

    schema = {
        "@type": "BlogPosting",
        "@id": f"{post_url}#blogposting",
        "url": post_url,
        "headline": post.seo_title or post.title,
        "name": post.title,
        "description": post.seo_description or post.excerpt or post.subtitle or post.title,
        "articleBody": post.excerpt or post.subtitle or post.title,
        "datePublished": post.published_at.isoformat() if post.published_at else post.created_at.isoformat(),
        "dateModified": post.updated_at.isoformat(),
        "author": {"@type": "Person", "name": author_name or "Majlesyar"},
        "publisher": {"@id": f"{base_url}/#organization"},
        "mainEntityOfPage": {"@id": f"{post_url}#webpage"},
        "inLanguage": "fa-IR",
    }
    if image_url:
        schema["image"] = [image_url]
    if post.category:
        schema["articleSection"] = post.category.name
    if post.seo_keywords:
        schema["keywords"] = ", ".join(str(keyword) for keyword in post.seo_keywords if str(keyword).strip())

    return [
        {
            "@type": "WebPage",
            "@id": f"{post_url}#webpage",
            "url": post_url,
            "name": post.seo_title or post.title,
            "description": post.seo_description or post.excerpt or post.subtitle or post.title,
            "isPartOf": {"@id": f"{base_url}/#website"},
            "inLanguage": "fa-IR",
        },
        schema,
        _breadcrumb_schema(base_url, [("Majlesyar", "/"), ("Blog", "/blog"), (post.title, f"/blog/{post.slug}")]),
    ]


def _event_structured_data(request, event_page: dict) -> list[dict]:
    base_url = request.build_absolute_uri("/").rstrip("/")
    route_path = _normalize_path(str(event_page.get("route_path") or f"/events/{event_page.get('slug', '')}"))
    page_url = f"{base_url}{route_path}"
    page_name = str(event_page.get("seo_title") or event_page.get("name") or "Majlesyar")
    description = str(event_page.get("seo_description") or event_page.get("description") or "")

    graph = [
        {
            "@type": "CollectionPage",
            "@id": f"{page_url}#collection",
            "url": page_url,
            "name": page_name,
            "description": description,
            "inLanguage": "fa-IR",
        },
        _breadcrumb_schema(base_url, _breadcrumb_items_for_route(_site_setting(), route_path)),
    ]

    products = _event_products(event_page)
    if products:
        graph[0]["mainEntity"] = {
            "@type": "ItemList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": index,
                    "url": f"{base_url}{product.public_path}",
                    "name": product.name,
                }
                for index, product in enumerate(products, start=1)
            ],
        }

    faqs = [
        faq
        for faq in (event_page.get("faqs") or [])
        if isinstance(faq, dict) and faq.get("question") and faq.get("answer")
    ]
    if faqs:
        graph.append(
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": str(faq["question"]),
                        "acceptedAnswer": {"@type": "Answer", "text": str(faq["answer"])},
                    }
                    for faq in faqs[:8]
                ],
            }
        )

    return graph


def _product_structured_data(request, product) -> list[dict]:
    base_url = request.build_absolute_uri("/").rstrip("/")
    product_url = f"{base_url}{product.public_path}"
    image_url = _product_image_url(request, product)
    site_setting = _site_setting()
    collection_path = _product_collection_url(request, product, site_setting)
    product_schema = {
        "@type": "Product",
        "@id": f"{product_url}#product",
        "name": product.name,
        "description": product.description or product.name,
        "sku": str(product.id),
        "url": product_url,
        "brand": {"@type": "Brand", "name": "Majlesyar"},
    }
    if image_url:
        product_schema["image"] = [image_url]
    if product.price:
        product_schema["offers"] = {
            "@type": "Offer",
            "url": product_url,
            "priceCurrency": "IRR",
            "price": str(int(product.price) * 10),
            "availability": "https://schema.org/InStock" if product.available else "https://schema.org/OutOfStock",
            "seller": {"@id": f"{base_url}/#organization"},
        }

    return [
        product_schema,
        _breadcrumb_schema(
            base_url,
            _breadcrumb_items_for_route(site_setting, collection_path, product.name, product.public_path),
        ),
    ]


def _structured_data_for_request(request) -> dict:
    site_setting = _site_setting()
    graph = _base_structured_data(request, site_setting)
    event_page = _event_page_for_path(request.path, site_setting)
    if event_page:
        graph.extend(_event_structured_data(request, event_page))
    elif (product := _product_for_path(request.path)) is not None and not product.is_temporary:
        graph.extend(_product_structured_data(request, product))
    elif (blog_post := _blog_post_for_path(request.path)) is not None:
        graph.extend(_blog_post_structured_data(request, blog_post))
    else:
        graph.extend(_static_page_structured_data(request, request.path, site_setting))

    return {"@context": "https://schema.org", "@graph": graph}


def _inject_structured_data(request, content: bytes) -> bytes:
    html = content.decode("utf-8")
    if "data-seo-server" in html or "</head>" not in html:
        return content
    scripts = _jsonld_scripts(_structured_data_for_request(request))
    return html.replace("</head>", f"    {scripts}\n  </head>", 1).encode("utf-8")


def _is_known_spa_path(path: str) -> bool:
    normalized_path = _normalize_path(path)
    if normalized_path in FORCED_NOT_FOUND_PATHS:
        return False
    if normalized_path == "/product" or normalized_path.startswith("/product/"):
        return False
    if normalized_path in STATIC_PUBLIC_PAGES:
        return True
    if any(
        normalized_path == prefix or normalized_path.startswith(f"{prefix}/")
        for prefix in PRIVATE_SPA_PREFIXES
    ):
        return True
    if normalized_path.startswith("/order/"):
        return True

    site_setting = _site_setting()
    if _event_page_for_path(normalized_path, site_setting):
        return True
    if normalized_path.startswith("/events/") and site_setting:
        slug = normalized_path.rsplit("/", 1)[-1]
        if any(
            isinstance(page, dict)
            and str(page.get("slug") or "").strip() == slug
            and not page.get("hidden")
            for page in (site_setting.event_pages or [])
        ):
            return True
    if _product_for_path(normalized_path) is not None:
        return True
    if _blog_post_for_path(normalized_path) is not None:
        return True
    return False


class SpaTemplateView(TemplateView):
    """Serve SPA HTML with CDN cache for public pages and no-store for private flows."""

    def get(self, request, *args, **kwargs):
        if not _is_known_spa_path(request.path):
            response = render(
                request,
                "errors/base.html",
                {
                    "status_code": 404,
                    "title": "صفحه پیدا نشد",
                    "message": "این آدرس وجود ندارد یا محصول آن حذف شده است.",
                    "hint": "از لینک‌های زیر برای ادامه بازدید استفاده کنید.",
                },
                status=404,
            )
            response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
            response.headers["Cache-Control"] = "no-store, max-age=0, must-revalidate"
            return response
        return super().get(request, *args, **kwargs)

    def render_to_response(self, context, **response_kwargs):
        response = super().render_to_response(context, **response_kwargs)
        request = self.request

        if hasattr(response, "add_post_render_callback"):
            response.add_post_render_callback(
                lambda rendered_response: _attach_structured_data(request, rendered_response)
            )

        path = request.path.rstrip("/") or "/"
        is_private = any(path == prefix or path.startswith(f"{prefix}/") for prefix in PRIVATE_SPA_PREFIXES)
        temporary_product = _temporary_product_for_path(request.path)
        if temporary_product:
            response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive, nosnippet"

        if is_private or temporary_product:
            response.headers["Cache-Control"] = "no-store, max-age=0, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        else:
            response.headers["Cache-Control"] = "public, max-age=0, s-maxage=600, stale-while-revalidate=86400"
            response.headers["Vary"] = "Accept-Encoding"
        return response


def _attach_structured_data(request, response):
    content_type = response.headers.get("Content-Type", "")
    if "text/html" not in content_type:
        return response
    try:
        response.content = _inject_structured_data(request, response.content)
    except (OperationalError, ProgrammingError, UnicodeDecodeError):
        return response
    response.headers["Content-Length"] = str(len(response.content))
    return response


NoCacheTemplateView = SpaTemplateView


@require_safe
def forced_not_found(request) -> HttpResponse:
    response = HttpResponse("Not Found", status=404, content_type="text/plain; charset=utf-8")
    response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    response.headers["Cache-Control"] = "no-store, max-age=0, must-revalidate"
    return response


@require_safe
def robots_txt(request) -> HttpResponse:
    sitemap_url = request.build_absolute_uri("/sitemap.xml")
    content = _read_file_text(
        [
            settings.FRONTEND_DIST_DIR / "robots.txt",
            settings.STATIC_ROOT / "robots.txt",
        ]
    )
    if content is None:
        content = _default_robots(sitemap_url)
    elif "Sitemap:" in content:
        lines = [
            f"Sitemap: {sitemap_url}" if line.strip().lower().startswith("sitemap:") else line
            for line in content.splitlines()
        ]
        content = "\n".join(lines) + ("\n" if not content.endswith("\n") else "")

    content = _strip_unknown_robots_directives(content)

    return _uncached_text_response(content, "text/plain; charset=utf-8")


@require_safe
def verification_6285703_txt(request) -> HttpResponse:
    content = _read_file_text(
        [
            settings.BASE_DIR.parent / "6285703.txt",
            settings.FRONTEND_DIST_DIR / "6285703.txt",
            settings.STATIC_ROOT / "6285703.txt",
        ]
    )
    return _uncached_text_response(content if content is not None else "", "text/plain; charset=utf-8")


@require_safe
def verification_8583454_txt(request) -> HttpResponse:
    content = _read_file_text(
        [
            settings.BASE_DIR.parent / "8583454.txt",
            settings.FRONTEND_DIST_DIR / "8583454.txt",
            settings.STATIC_ROOT / "8583454.txt",
        ]
    )
    return _uncached_text_response(content if content is not None else "", "text/plain; charset=utf-8")


def _default_llms_txt(request) -> str:
    base_url = request.build_absolute_uri("/").rstrip("/")
    return "\n".join(
        [
            "# Majlesyar",
            "",
            "Majlesyar is a Persian ecommerce and event-services website for ceremony products, flower arrangements, food packs, and related ordering workflows in Tehran and Karaj.",
            "",
            "## Website",
            "",
            f"- [Home]({base_url}/)",
            f"- [Products]({base_url}/pack)",
            f"- [Flowers]({base_url}/flower)",
            f"- [Food]({base_url}/food)",
            f"- [Halva and dates]({base_url}/halva-khorma)",
            f"- [Blog]({base_url}/blog)",
            f"- [Contact]({base_url}/contact)",
            f"- [Sitemap]({base_url}/sitemap.xml)",
            "",
            "## Crawling",
            "",
            "Public product, category, blog, and information pages may be crawled for search and assistant answers. Do not crawl private customer dashboards, checkout flows, admin pages, API mutation endpoints, or authentication endpoints.",
            "",
        ]
    )


@require_safe
def llms_txt(request) -> HttpResponse:
    content = _read_file_text(
        [
            settings.FRONTEND_DIST_DIR / "llms.txt",
            settings.STATIC_ROOT / "llms.txt",
        ]
    )
    return _uncached_text_response(content if content is not None else _default_llms_txt(request), "text/markdown; charset=utf-8")


@require_safe
def favicon_redirect(request):
    try:
        from site_settings.models import SiteSetting

        site_setting = SiteSetting.load()
    except (OperationalError, ProgrammingError):
        site_setting = None

    if site_setting and site_setting.site_favicon:
        return redirect(site_setting.site_favicon.url, permanent=False)

    return redirect(static_url("favicon.ico"), permanent=False)


@require_safe
def sitemap_xml(request) -> HttpResponse:
    content = _read_file_text(
        [
            settings.FRONTEND_DIST_DIR / "sitemap.xml",
            settings.STATIC_ROOT / "sitemap.xml",
        ]
    )
    if content is None:
        content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>
"""
    return _uncached_text_response(content, "application/xml; charset=utf-8")
