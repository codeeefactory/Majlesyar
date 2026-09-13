from django.urls import path

from .views import (
    ScrapeJobDetailAPIView,
    ScrapeJobListCreateAPIView,
    ScrapeJobRefreshAPIView,
    ScrapeJobResultsAPIView,
    ScraperHealthAPIView,
)

urlpatterns = [
    path("health/", ScraperHealthAPIView.as_view(), name="maps-scraper-health"),
    path("jobs/", ScrapeJobListCreateAPIView.as_view(), name="maps-scraper-jobs"),
    path("jobs/<uuid:pk>/", ScrapeJobDetailAPIView.as_view(), name="maps-scraper-job-detail"),
    path("jobs/<uuid:pk>/refresh/", ScrapeJobRefreshAPIView.as_view(), name="maps-scraper-job-refresh"),
    path("jobs/<uuid:pk>/results/", ScrapeJobResultsAPIView.as_view(), name="maps-scraper-job-results"),
]
