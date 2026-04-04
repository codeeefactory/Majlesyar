from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import TestCase, override_settings


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
        self.assertNotIn("Content-Signal", response.content.decode("utf-8"))
        self.assertNotIn("Content-Signal", response.headers)
