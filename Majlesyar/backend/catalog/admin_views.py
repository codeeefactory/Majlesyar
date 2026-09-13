from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import redirect
from django.urls import reverse

from .cloudflare import purge_cloudflare_cache


def purge_cloudflare_cache_view(request: HttpRequest) -> HttpResponse:
    if not request.user.is_superuser:
        raise PermissionDenied
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    result = purge_cloudflare_cache()
    if result.purged_everything:
        messages.success(request, "کش Cloudflare با موفقیت پاک شد.")
    else:
        messages.warning(request, result.error or "کش Cloudflare پاک نشد.")
    return redirect(reverse("admin:index"))
