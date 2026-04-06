from django.test import TestCase


class PingAPIViewTests(TestCase):
    def test_ping_endpoint_returns_uncached_success_payload(self):
        response = self.client.get("/api/v1/ping/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["ok"], True)
        self.assertIn("server_time", response.json())
        self.assertEqual(
            response.headers["Cache-Control"],
            "no-store, no-cache, must-revalidate, max-age=0",
        )
        self.assertEqual(response.headers["Pragma"], "no-cache")
        self.assertEqual(response.headers["Expires"], "0")
