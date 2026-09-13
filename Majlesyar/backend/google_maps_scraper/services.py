from __future__ import annotations

import csv
import io
from typing import Any

import requests
from django.conf import settings
from django.utils import timezone

from .models import MapsScrapeJob


LEAD_FIELDS = ("title", "phone", "emails", "website", "category", "address", "review_rating", "review_count")


class ScraperUnavailable(RuntimeError):
    pass


class ScraperClient:
    def __init__(self):
        config = settings.GOOGLE_MAPS_SCRAPER
        self.base_url = config["BASE_URL"]
        self.api_key = config["API_KEY"]
        self.timeout = (config["CONNECT_TIMEOUT"], config["READ_TIMEOUT"])

    def request(self, method: str, path: str, **kwargs) -> requests.Response:
        headers = kwargs.pop("headers", {})
        headers.setdefault("User-Agent", "Majlesyar/google-maps-scraper-kit")
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        try:
            response = requests.request(
                method,
                f"{self.base_url}{path}",
                headers=headers,
                timeout=self.timeout,
                **kwargs,
            )
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            detail = ""
            if getattr(exc, "response", None) is not None:
                detail = f": {exc.response.text[:500]}"
            raise ScraperUnavailable(f"Google Maps scraper request failed{detail}") from exc

    def health(self) -> list[dict[str, Any]]:
        return self.request("GET", "/api/v1/jobs").json()

    def create(self, payload: dict) -> str:
        response = self.request("POST", "/api/v1/jobs", json=payload)
        job_id = response.json().get("id")
        if not job_id:
            raise ScraperUnavailable("Google Maps scraper returned no job id.")
        return str(job_id)

    def detail(self, job_id: str) -> dict:
        return self.request("GET", f"/api/v1/jobs/{job_id}").json()

    def download(self, job_id: str) -> bytes:
        return self.request("GET", f"/api/v1/jobs/{job_id}/download").content

    def delete(self, job_id: str) -> None:
        self.request("DELETE", f"/api/v1/jobs/{job_id}")


def refresh_job(job: MapsScrapeJob, client: ScraperClient | None = None) -> MapsScrapeJob:
    client = client or ScraperClient()
    payload = client.detail(job.upstream_id)
    upstream_status = str(payload.get("Status", payload.get("status", job.status))).lower()
    if upstream_status not in MapsScrapeJob.Status.values:
        upstream_status = job.status
    job.status = upstream_status
    job.upstream_payload = payload
    if upstream_status in {MapsScrapeJob.Status.OK, MapsScrapeJob.Status.FAILED} and not job.completed_at:
        job.completed_at = timezone.now()
    if upstream_status == MapsScrapeJob.Status.FAILED:
        job.error_message = str(payload.get("Error", payload.get("error", "Upstream scrape failed.")))[:2000]
    job.save(update_fields=["status", "upstream_payload", "completed_at", "error_message", "updated_at"])
    return job


def parse_results(raw_csv: bytes, *, full: bool = False) -> list[dict[str, str]]:
    text = raw_csv.decode("utf-8-sig", "replace")
    rows = list(csv.DictReader(io.StringIO(text)))
    if full:
        return [dict(row) for row in rows]
    return [{field: row.get(field, "") for field in LEAD_FIELDS} for row in rows]
