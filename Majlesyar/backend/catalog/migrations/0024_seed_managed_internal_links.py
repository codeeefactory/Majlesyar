from django.db import migrations, models


REMOVED_PATHS = {
    "/pack/personal",
    "/pack/memorial/luxury",
    "/flower/funeral-bouquet",
    "/halva-khorma/luxury",
    "/food/charcuterie-board",
    "/food/juice",
}

DEFAULT_PAGES = [
    {"name": "فینگر فود", "route_path": "/food/finger_food"},
    {"name": "ترحیم", "route_path": "/pack/memorial"},
    {"name": "حلوا و خرما", "route_path": "/halva-khorma"},
    {"name": "گل", "route_path": "/flower"},
    {"name": "منوی فود", "route_path": "/food"},
    {"name": "شله زرد", "route_path": "/food/shaleh-zard"},
    {"name": "پک پذیرایی", "route_path": "/pack"},
    {"name": "تاج گل ترحیم", "route_path": "/flower/memorial-wreaths"},
    {"name": "دسته گل", "route_path": "/flower/bouquets"},
    {"name": "تاج گل تبریک", "route_path": "/flower/congratulatory-wreaths"},
    {"name": "باکس گل", "route_path": "/flower/box"},
]

MEMORIAL_LINKS = [
    {"label": "حلوا خرما و خرما گردو", "url": "/halva-khorma"},
    {"label": "تاج گل‌های ترحیم و تسلیت", "url": "/flower/memorial-wreaths"},
    {"label": "فینگر فود", "url": "/food/finger_food"},
    {"label": "ساخت پک اختصاصی", "url": "/builder"},
]

FALLBACK_LINKS = {
    "/food/finger_food": [
        {"label": "پک میوه و پذیرایی", "url": "/pack"},
        {"label": "خانه", "url": "/"},
    ],
    "/pack/memorial": [
        *MEMORIAL_LINKS,
        {"label": "خانه", "url": "/"},
    ],
    "/halva-khorma": [
        {"label": "شله زرد", "url": "/food/shaleh-zard"},
        {"label": "دسته گل", "url": "/flower/bouquets"},
        {"label": "پک‌های ترحیم و ختم", "url": "/pack/memorial"},
        {"label": "خانه", "url": "/"},
    ],
    "/flower": [
        {"label": "تاج گل‌های ترحیم و تسلیت", "url": "/flower/memorial-wreaths"},
        {"label": "دسته گل", "url": "/flower/bouquets"},
        {"label": "باکس گل", "url": "/flower/box"},
        {"label": "حلوا خرما و خرما گردو", "url": "/halva-khorma"},
        {"label": "فینگر فود", "url": "/food/finger_food"},
        {"label": "خانه", "url": "/"},
    ],
    "/pack": [
        {"label": "پک‌های ترحیم و ختم", "url": "/pack/memorial"},
        {"label": "حلوا خرما و خرما گردو", "url": "/halva-khorma"},
        {"label": "تاج گل‌های ترحیم و تسلیت", "url": "/flower/memorial-wreaths"},
        {"label": "خانه", "url": "/"},
    ],
    "/flower/memorial-wreaths": [
        {"label": "خانه", "url": "/"},
        {"label": "حلوا خرما و خرما گردو", "url": "/halva-khorma"},
    ],
    "/flower/bouquets": [
        {"label": "باکس گل", "url": "/flower/box"},
        {"label": "فینگر فود", "url": "/food/finger_food"},
        {"label": "خانه", "url": "/"},
    ],
    "/flower/congratulatory-wreaths": [
        {"label": "فینگر فود", "url": "/food/finger_food"},
        {"label": "خانه", "url": "/"},
    ],
    "/flower/box": [
        {"label": "دسته گل", "url": "/flower/bouquets"},
        {"label": "فینگر فود", "url": "/food/finger_food"},
        {"label": "خانه", "url": "/"},
    ],
    "/food": [
        {"label": "فینگر فود", "url": "/food/finger_food"},
        {"label": "شله زرد", "url": "/food/shaleh-zard"},
        {"label": "خانه", "url": "/"},
    ],
    "/food/shaleh-zard": [
        {"label": "حلوا خرما و خرما گردو", "url": "/halva-khorma"},
        {"label": "خانه", "url": "/"},
    ],
}


def normalize_path(value):
    raw = str(value or "").strip()
    if not raw:
        return ""
    path = "/" + "/".join(part for part in raw.split("/") if part)
    return path.rstrip("/") or "/"


def seed_internal_links(apps, schema_editor):
    InternalLink = apps.get_model("catalog", "InternalLink")
    InternalLinkSource = apps.get_model("catalog", "InternalLinkSource")
    SiteSetting = apps.get_model("site_settings", "SiteSetting")

    setting = SiteSetting.objects.order_by("pk").first()
    stored_pages = list(setting.event_pages or []) if setting else []
    pages = [page for page in stored_pages if isinstance(page, dict)] or list(DEFAULT_PAGES)

    usable_pages = []
    for page in pages:
        route = normalize_path(page.get("route_path") or f"/events/{page.get('slug', '')}")
        if not route or route in REMOVED_PATHS or page.get("hidden") or page.get("available") is False:
            continue
        usable_pages.append({**page, "route_path": route})

    candidates = {}

    def add_candidate(source, label, target):
        source_path = normalize_path(source)
        target_path = normalize_path(target)
        label_text = str(label or "").strip()
        if not source_path or not target_path or not label_text or target_path in REMOVED_PATHS:
            return
        if target_path == "/pack/memorial" and label_text in {"ترحیم", "پک ترحیم"}:
            label_text = "پک‌های ترحیم و ختم"
        rows = candidates.setdefault(source_path, [])
        if not any(row["url"] == target_path for row in rows):
            rows.append({"label": label_text, "url": target_path})

    for link in MEMORIAL_LINKS:
        add_candidate("/pack/memorial", link["label"], link["url"])

    for page in usable_pages:
        source = page["route_path"]
        for link in page.get("internal_links") or []:
            if isinstance(link, dict):
                add_candidate(source, link.get("label"), link.get("url"))

        source_depth = len([part for part in source.split("/") if part])
        for child in usable_pages:
            target = child["route_path"]
            target_depth = len([part for part in target.split("/") if part])
            if target.startswith(f"{source}/") and target_depth == source_depth + 1:
                add_candidate(source, child.get("name") or child.get("slug"), target)

    for source, links in FALLBACK_LINKS.items():
        if candidates.get(source):
            continue
        for link in links:
            add_candidate(source, link["label"], link["url"])

    for source, links in candidates.items():
        for index, link in enumerate(links, start=1):
            obj, created = InternalLink.objects.get_or_create(
                source_path=source,
                target_url=link["url"],
                defaults={
                    "label": link["label"],
                    "position": index * 10,
                    "is_active": True,
                },
            )
            if not created and obj.target_url == "/pack/memorial" and obj.label in {"ترحیم", "پک ترحیم"}:
                obj.label = "پک‌های ترحیم و ختم"
                obj.save(update_fields=["label"])

    managed_sources = set(candidates)
    managed_sources.update(InternalLink.objects.values_list("source_path", flat=True))
    for source in managed_sources:
        InternalLinkSource.objects.get_or_create(path=source)


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0023_product_and_builder_item_3d_assets"),
        ("site_settings", "0011_restore_core_event_pages"),
    ]

    operations = [
        migrations.CreateModel(
            name="InternalLinkSource",
            fields=[
                ("path", models.CharField(max_length=500, primary_key=True, serialize=False, verbose_name="مسیر صفحه")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "منبع مدیریت لینک داخلی",
                "verbose_name_plural": "منابع مدیریت لینک داخلی",
                "ordering": ["path"],
            },
        ),
        migrations.RunPython(seed_internal_links, migrations.RunPython.noop),
    ]
