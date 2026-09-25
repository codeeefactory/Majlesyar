from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import TestCase, override_settings

from blog.models import BlogPost
from catalog.models import Product


def _server_jsonld(content: str) -> dict:
    marker = '<script type="application/ld+json" data-seo-server>'
    graph = []
    start = 0
    while True:
        try:
            script_start = content.index(marker, start) + len(marker)
            script_end = content.index("</script>", script_start)
        except ValueError:
            break
        graph.append(json.loads(content[script_start:script_end]))
        start = script_end
    return {"@context": "https://schema.org", "@graph": graph}


@override_settings(SECURE_SSL_REDIRECT=False)
class RobotsTxtTests(TestCase):
    def test_robots_txt_strips_content_signal_from_body_and_headers(self):
        with TemporaryDirectory() as tmp_dir:
            robots_path = Path(tmp_dir) / "robots.txt"
            robots_path.write_text(
                "\n".join(
                    [
                        "User-agent: *",
                        "Allow: /",
                        "Content-Signal: search=yes,ai-train=no",
                        "Sitemap: https://example.com/sitemap.xml",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            with override_settings(FRONTEND_DIST_DIR=Path(tmp_dir), STATIC_ROOT=Path(tmp_dir)):
                response = self.client.get(
                    "/robots.txt",
                    HTTP_CONTENT_SIGNAL="search=yes,ai-train=no",
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Cache-Control"], "no-store, max-age=0, must-revalidate")
        self.assertNotIn("Content-Signal", response.content.decode("utf-8"))
        self.assertNotIn("Content-Signal", response.headers)

    def test_robots_txt_does_not_list_sensitive_routes(self):
        response = self.client.get("/robots.txt")
        content = response.content.decode("utf-8").lower()

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("/admin", content)
        self.assertNotIn("/checkout", content)
        self.assertNotIn("/order", content)

    def test_robots_txt_explicitly_allows_major_ai_crawlers(self):
        with TemporaryDirectory() as tmp_dir:
            with override_settings(FRONTEND_DIST_DIR=Path(tmp_dir), STATIC_ROOT=Path(tmp_dir)):
                response = self.client.get("/robots.txt")
        content = response.content.decode("utf-8")

        for agent in (
            "GPTBot",
            "ClaudeBot",
            "PerplexityBot",
            "Googlebot",
            "Applebot-Extended",
            "Bytespider",
            "Amazonbot",
        ):
            with self.subTest(agent=agent):
                self.assertIn(f"User-agent: {agent}\nAllow: /", content)


@override_settings(SECURE_SSL_REDIRECT=False)
class LlmsTxtTests(TestCase):
    def test_llms_txt_is_markdown_with_h1_and_links(self):
        response = self.client.get("/llms.txt", secure=True)
        content = response.content.decode("utf-8")

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/markdown", response.headers["Content-Type"])
        self.assertEqual(response.headers["Cache-Control"], "no-store, max-age=0, must-revalidate")
        self.assertIn("Last-Modified", response.headers)
        self.assertTrue(content.startswith("# "))
        self.assertTrue(content.splitlines()[2].startswith("> "))
        self.assertGreaterEqual(content.count("\n## "), 8)
        for section in ("Permitted", "Restricted", "Pricing", "Contact", "Citation and attribution", "Optional"):
            with self.subTest(section=section):
                self.assertIn(f"## {section}", content)
        self.assertIn("free to crawl", content)
        self.assertIn("Source: Majlesyar", content)
        self.assertIn("- [Home](https://", content)
        self.assertRegex(content, r"(?m)^- \[[^]]+\]\(https://[^)]+\): .+$")
        self.assertIn("sitemap.xml", content)


@override_settings(SECURE_SSL_REDIRECT=False)
class SitemapTests(TestCase):
    def test_sitemap_contains_current_public_content_only(self):
        product = Product.objects.create(name="Indexed Product", url_slug="indexed-product", available=True)
        temporary_product = Product.objects.create(
            name="Temporary Product",
            url_slug="temporary-sitemap-product",
            available=True,
            is_temporary=True,
        )
        Product.objects.create(
            name="Forced Missing Product",
            url_slug="forced-missing-product",
            public_path="/food/juice",
            available=True,
        )
        published_post = BlogPost.objects.create(
            title="Published Sitemap Post",
            slug="published-sitemap-post",
            content="Published content",
            status=BlogPost.Status.PUBLISHED,
        )
        draft_post = BlogPost.objects.create(
            title="Draft Sitemap Post",
            slug="draft-sitemap-post",
            content="Draft content",
            status=BlogPost.Status.DRAFT,
        )

        response = self.client.get("/sitemap.xml", secure=True)
        content = response.content.decode("utf-8")

        self.assertEqual(response.status_code, 200)
        self.assertIn("application/xml", response.headers["Content-Type"])
        self.assertIn("<loc>https://testserver/</loc>", content)
        self.assertIn(f"<loc>https://testserver{product.public_path}</loc>", content)
        self.assertIn(f"<loc>https://testserver/blog/{published_post.slug}</loc>", content)
        self.assertIn("<lastmod>", content)
        self.assertNotIn(temporary_product.public_path, content)
        self.assertNotIn(draft_post.slug, content)
        self.assertNotIn("/food/juice", content)
        self.assertNotIn("/track", content)


@override_settings(SECURE_SSL_REDIRECT=False)
class StructuredDataTests(TestCase):
    def test_public_spa_html_contains_server_jsonld(self):
        response = self.client.get("/")
        content = response.content.decode("utf-8")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["Link"],
            '<http://testserver/llms.txt>; rel="describedby"; type="text/markdown"',
        )
        self.assertIn('type="application/ld+json"', content)
        self.assertIn('"@context":"https://schema.org"', content)
        self.assertIn('"WebSite"', content)
        self.assertIn('"name":"مجلس یار"', content)
        self.assertIn('"alternateName":"مجلس‌یار"', content)
        self.assertIn('"LocalBusiness"', content)
        self.assertIn('"@type":"WebPage"', content)
        self.assertIn('"@type":"PostalAddress"', content)
        self.assertIn('"@type":"ContactPoint"', content)
        self.assertIn('"@type":"GeoCoordinates"', content)
        self.assertIn('"@type":"AdministrativeArea"', content)
        self.assertNotIn('"priceRange"', content)
        self.assertIn('"streetAddress"', content)
        self.assertIn('"addressLocality":"تهران"', content)
        self.assertIn('"addressRegion":"تهران"', content)
        self.assertIn('"postalCode":"1439814383"', content)
        self.assertIn('"addressCountry":"IR"', content)

    def test_static_public_spa_routes_contain_webpage_schema(self):
        expected = {
            "/about": '"@type":"AboutPage"',
            "/contact": '"@type":"ContactPage"',
            "/blog": '"@type":"Blog"',
            "/terms": '"@type":"WebPage"',
            "/builder": '"@type":"WebApplication"',
            "/cart": '"@type":"WebPage"',
            "/track": '"@type":"WebPage"',
        }

        for path, schema_type in expected.items():
            with self.subTest(path=path):
                response = self.client.get(path)
                content = response.content.decode("utf-8")

                self.assertEqual(response.status_code, 200)
                self.assertIn('type="application/ld+json"', content)
                self.assertIn(schema_type, content)
                self.assertIn('"@type":"BreadcrumbList"', content)

    def test_event_page_html_contains_rich_result_schemas(self):
        Product.objects.create(
            name="Collection Schema Product",
            url_slug="collection-schema-product",
            description="Collection schema test item.",
            event_types=["halva-khorma"],
            available=True,
        )
        Product.objects.create(
            name="Temporary Collection Product",
            url_slug="temporary-collection-product",
            description="Temporary collection schema test item.",
            event_types=["halva-khorma"],
            available=True,
            is_temporary=True,
        )

        response = self.client.get("/halva-khorma")
        content = response.content.decode("utf-8")
        payload = _server_jsonld(content)
        graph = payload["@graph"]
        collection = next(item for item in graph if item.get("@type") == "CollectionPage")

        self.assertEqual(response.status_code, 200)
        self.assertIn('"@type":"CollectionPage"', content)
        self.assertIn('"@type":"BreadcrumbList"', content)
        self.assertIn('"@type":"FAQPage"', content)
        self.assertEqual(collection["mainEntity"]["@type"], "ItemList")
        self.assertIn("Collection Schema Product", [item["name"] for item in collection["mainEntity"]["itemListElement"]])
        self.assertNotIn("Temporary Collection Product", [item["name"] for item in collection["mainEntity"]["itemListElement"]])
        self.assertNotIn('"@type":["Organization","LocalBusiness"]', content)
        self.assertNotIn('"@type":"Product"', content)

    def test_product_page_html_contains_product_offer_schema(self):
        product = Product.objects.create(
            name="Rich Result Product",
            url_slug="rich-result-product",
            description="Product schema test item.",
            price=120000,
            event_types=["memorial"],
            available=True,
        )

        response = self.client.get(product.public_path)
        content = response.content.decode("utf-8")
        payload = _server_jsonld(content)
        graph = payload["@graph"]
        breadcrumb = next(item for item in graph if item.get("@type") == "BreadcrumbList")
        breadcrumb_names = [item["name"] for item in breadcrumb["itemListElement"]]

        self.assertEqual(response.status_code, 200)
        self.assertIn('"@type":"Product"', content)
        self.assertIn('"@type":"Offer"', content)
        self.assertIn('"priceCurrency":"IRR"', content)
        self.assertIn('"price":"1200000"', content)
        self.assertNotIn("Products", breadcrumb_names)
        self.assertEqual(breadcrumb_names[-1], "Rich Result Product")

    def test_temporary_product_page_is_noindexed_and_has_no_product_schema(self):
        product = Product.objects.create(
            name="Temporary Product",
            url_slug="temporary-product",
            description="Temporary product test item.",
            price=120000,
            event_types=["memorial"],
            available=True,
            is_temporary=True,
        )

        response = self.client.get(product.public_path)
        content = response.content.decode("utf-8")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["X-Robots-Tag"],
            "noindex, nofollow, noarchive, nosnippet",
        )
        self.assertEqual(response.headers["Cache-Control"], "no-store, max-age=0, must-revalidate")
        self.assertNotIn('"@type":"Product"', content)
        self.assertNotIn("Temporary Product", content)

    def test_legacy_product_prefix_and_deleted_urls_return_real_404(self):
        Product.objects.create(name="Old Product", url_slug="old-product", available=True)

        for path in ("/product", "/product/old-product", "/product/deleted-product", "/pack/deleted-product"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 404)
            self.assertContains(response, "ساخت پک اختصاصی", status_code=404)

    def test_removed_collection_and_media_urls_return_real_404(self):
        removed_paths = (
            "/pack/personal",
            "/pack/memorial/luxury",
            "/flower/funeral-bouquet",
            "/halva-khorma/luxury",
            "/food/charcuterie-board",
            "/food/juice",
            "/media/products/optimized/aza/8b380b32e31e/320/پک عزا.avif",
            "/media/products/optimized/aza/8b380b32e31e/480/پک عزا.avif",
            "/media/products/optimized/aza/8b380b32e31e/960/پک عزا.avif",
        )

        for path in removed_paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.headers["X-Robots-Tag"], "noindex, nofollow, noarchive")

    def test_blog_post_page_html_contains_blogposting_schema(self):
        BlogPost.objects.create(
            title="Rich Result Blog Post",
            slug="rich-result-blog-post",
            excerpt="Blog post schema test excerpt.",
            content="Blog post schema test content.",
            status=BlogPost.Status.PUBLISHED,
        )

        response = self.client.get("/blog/rich-result-blog-post")
        content = response.content.decode("utf-8")

        self.assertEqual(response.status_code, 200)
        self.assertIn('"@type":"BlogPosting"', content)
        self.assertIn('"@type":"BreadcrumbList"', content)
        self.assertIn('"headline":"Rich Result Blog Post"', content)


@override_settings(SECURE_SSL_REDIRECT=False)
class SecurityHardeningTests(TestCase):
    def test_sensitive_probe_paths_do_not_hit_spa_fallback(self):
        for path in (
            "/.git/HEAD",
            "/.env",
            "/backup.zip",
            "/backup.tar.gz",
            "/db.sql",
            "/config.php",
            "/logs/",
            "/phpinfo.php",
            "/wp-admin/",
            "/admin/",
            "/assets/app.js.map",
            "/static/assets/chunk.js.map",
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 404)
                self.assertNotIn(b"<!doctype html>", response.content.lower())
                self.assertIn("Content-Security-Policy", response.headers)
                self.assertIn("Permissions-Policy", response.headers)

    def test_bare_order_path_redirects_to_tracking(self):
        for path in ("/order", "/order/"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.headers["Location"], "/track")

    @override_settings(SECURE_HSTS_SECONDS=63072000, SECURE_HSTS_INCLUDE_SUBDOMAINS=True, SECURE_HSTS_PRELOAD=True)
    def test_security_headers_are_present(self):
        response = self.client.get("/")

        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        csp = response.headers["Content-Security-Policy"]
        self.assertIn("default-src 'self'", csp)
        self.assertIn("script-src 'self' https://static.cloudflareinsights.com", csp)
        self.assertIn("connect-src 'self' https://majlesyar.com https://www.majlesyar.com https://cloudflareinsights.com", csp)
        self.assertNotIn("script-src 'self' 'unsafe-inline'", csp)
        self.assertIn("frame-ancestors 'none'", csp)
        self.assertIn("require-trusted-types-for 'script'", csp)
        self.assertIn("trusted-types default", csp)
        self.assertIn("camera=()", response.headers["Permissions-Policy"])
        self.assertEqual(response.headers["Referrer-Policy"], "same-origin")

        secure_response = self.client.get("/", secure=True)
        self.assertIn("max-age=63072000", secure_response.headers["Strict-Transport-Security"])
        self.assertIn("includeSubDomains", secure_response.headers["Strict-Transport-Security"])
        self.assertIn("preload", secure_response.headers["Strict-Transport-Security"])

    def test_private_spa_routes_are_noindexed(self):
        for path in ("/checkout", "/dashboard", "/login", "/profile", "/signup", "/admin/login", "/admin/orders"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers["X-Robots-Tag"], "noindex, nofollow, noarchive")

    @override_settings(LOGIN_RATE_LIMIT_ATTEMPTS=1, LOGIN_RATE_LIMIT_WINDOW_SECONDS=60)
    def test_login_rate_limit_applies_to_jwt_login(self):
        first = self.client.post("/api/v1/auth/token/", {"username": "missing", "password": "bad"})
        second = self.client.post("/api/v1/auth/token/", {"username": "missing", "password": "bad"})

        self.assertNotEqual(first.status_code, 429)
        self.assertEqual(second.status_code, 429)
        self.assertEqual(second.headers["Retry-After"], "60")
