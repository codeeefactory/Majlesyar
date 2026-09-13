from __future__ import annotations

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import MapsScrapeJob
from .permissions import IsStaffUser
from .serializers import MapsScrapeCreateSerializer, MapsScrapeJobSerializer
from .services import ScraperClient, ScraperUnavailable, parse_results, refresh_job


def upstream_error(exc: ScraperUnavailable) -> Response:
    return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class ScraperHealthAPIView(APIView):
    permission_classes = [IsStaffUser]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        try:
            jobs = ScraperClient().health()
        except ScraperUnavailable as exc:
            return upstream_error(exc)
        return Response({"ok": True, "upstream_jobs": len(jobs)})


class ScrapeJobListCreateAPIView(APIView):
    permission_classes = [IsStaffUser]

    @extend_schema(responses=MapsScrapeJobSerializer(many=True))
    def get(self, request):
        queryset = MapsScrapeJob.objects.all()
        requested_status = request.query_params.get("status")
        if requested_status:
            queryset = queryset.filter(status=requested_status)
        return Response(MapsScrapeJobSerializer(queryset[:200], many=True).data)

    @extend_schema(request=MapsScrapeCreateSerializer, responses={201: MapsScrapeJobSerializer})
    def post(self, request):
        serializer = MapsScrapeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        upstream_payload = serializer.to_upstream_payload()
        try:
            upstream_id = ScraperClient().create(upstream_payload)
        except ScraperUnavailable as exc:
            return upstream_error(exc)
        job = MapsScrapeJob.objects.create(
            upstream_id=upstream_id,
            name=serializer.validated_data["name"],
            keywords=serializer.validated_data["keywords"],
            latitude=serializer.validated_data["lat"],
            longitude=serializer.validated_data["lon"],
            request_payload={key: value for key, value in upstream_payload.items() if key != "proxies"},
            status=MapsScrapeJob.Status.WORKING,
            created_by=request.user,
        )
        return Response(MapsScrapeJobSerializer(job).data, status=status.HTTP_201_CREATED)


class ScrapeJobDetailAPIView(APIView):
    permission_classes = [IsStaffUser]

    @extend_schema(responses=MapsScrapeJobSerializer)
    def get(self, request, pk):
        job = get_object_or_404(MapsScrapeJob, pk=pk)
        if request.query_params.get("refresh", "1").lower() not in {"0", "false", "no"}:
            try:
                refresh_job(job)
            except ScraperUnavailable as exc:
                return upstream_error(exc)
        return Response(MapsScrapeJobSerializer(job).data)

    @extend_schema(responses={204: None})
    def delete(self, request, pk):
        job = get_object_or_404(MapsScrapeJob, pk=pk)
        try:
            ScraperClient().delete(job.upstream_id)
        except ScraperUnavailable as exc:
            return upstream_error(exc)
        job.status = MapsScrapeJob.Status.DELETED
        job.save(update_fields=["status", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class ScrapeJobRefreshAPIView(APIView):
    permission_classes = [IsStaffUser]

    @extend_schema(request=None, responses=MapsScrapeJobSerializer)
    def post(self, request, pk):
        job = get_object_or_404(MapsScrapeJob, pk=pk)
        try:
            refresh_job(job)
        except ScraperUnavailable as exc:
            return upstream_error(exc)
        return Response(MapsScrapeJobSerializer(job).data)


class ScrapeJobResultsAPIView(APIView):
    permission_classes = [IsStaffUser]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request, pk):
        job = get_object_or_404(MapsScrapeJob, pk=pk)
        try:
            refresh_job(job)
            if job.status != MapsScrapeJob.Status.OK:
                return Response(
                    {"detail": "Results are not ready.", "status": job.status},
                    status=status.HTTP_409_CONFLICT,
                )
            raw = ScraperClient().download(job.upstream_id)
        except ScraperUnavailable as exc:
            return upstream_error(exc)
        if request.query_params.get("format") == "csv":
            response = HttpResponse(raw, content_type="text/csv; charset=utf-8")
            response["Content-Disposition"] = f'attachment; filename="maps-{job.id}.csv"'
            return response
        rows = parse_results(raw, full=request.query_params.get("full") in {"1", "true", "yes"})
        job.result_count = len(rows)
        job.save(update_fields=["result_count", "updated_at"])
        return Response({"job": str(job.id), "count": len(rows), "results": rows})
