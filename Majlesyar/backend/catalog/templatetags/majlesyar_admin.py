from __future__ import annotations

from django import template

from config.admin_branding import get_admin_theme_manifest


register = template.Library()


@register.simple_tag(takes_context=True)
def admin_theme_manifest(context):
    return get_admin_theme_manifest(context.get("request"))
