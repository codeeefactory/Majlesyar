from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import MapsScrapeJob


class MapsScraperApiTests(APITestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username="maps-operator",
            password="pass12345",
            is_staff=True,
        )
        self.client.force_authenticate(self.staff)

    def payload(self):
        return {
            "name": "Tehran florists",
            "keywords": ["florists in Tehran", "florists in Tehran"],
            "lat": "35.6892000",
            "lon": "51.3890000",
            "depth": 5,
            "max_time": 300,
        }

    @patch("google_maps_scraper.views.ScraperClient.create", return_value="upstream-123")
    def test_staff_can_create_persistent_job(self, mocked_create):
        response = self.client.post(reverse("maps-scraper-jobs"), self.payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        job = MapsScrapeJob.objects.get()
        self.assertEqual(job.upstream_id, "upstream-123")
        self.assertEqual(job.keywords, ["florists in Tehran"])
        self.assertNotIn("proxies", job.request_payload)
        upstream = mocked_create.call_args.args[0]
        self.assertEqual(upstream["lat"], "35.6892000")
        self.assertTrue(upstream["email"])

    def test_non_staff_cannot_use_feature(self):
        user = get_user_model().objects.create_user(username="customer", password="pass12345")
        self.client.force_authenticate(user)
        response = self.client.get(reverse("maps-scraper-jobs"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch(
        "google_maps_scraper.services.ScraperClient.detail",
        return_value={"Status": "ok"},
    )
    @patch(
        "google_maps_scraper.views.ScraperClient.download",
        return_value=(
            b"title,phone,emails,website,category,address,review_rating,review_count,place_id\n"
            b"Shop,+98123,a@example.com,https://example.com,Florist,Tehran,4.8,12,secret-place\n"
        ),
    )
    def test_results_default_to_lead_fields(self, mocked_download, mocked_detail):
        job = MapsScrapeJob.objects.create(
            upstream_id="upstream-ok",
            name="Done",
            keywords=["florists"],
            latitude="35.6892",
            longitude="51.3890",
            created_by=self.staff,
        )
        response = self.client.get(reverse("maps-scraper-job-results", kwargs={"pk": job.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertNotIn("place_id", response.data["results"][0])
        self.assertEqual(response.data["results"][0]["title"], "Shop")

    @patch("google_maps_scraper.views.ScraperClient.create", side_effect=Exception("should not call"))
    def test_invalid_coordinates_are_rejected_before_upstream(self, mocked_create):
        payload = self.payload()
        payload["lat"] = "120"
        response = self.client.post(reverse("maps-scraper-jobs"), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mocked_create.assert_not_called()
