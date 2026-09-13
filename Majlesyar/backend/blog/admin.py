from django.contrib import admin
from django.utils.html import format_html

from config.admin_mixins import PersianAdminFormMixin

from .models import BlogCategory, BlogComment, BlogPost, BlogTag


@admin.register(BlogCategory)
class BlogCategoryAdmin(PersianAdminFormMixin, admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "display_order", "updated_at")
    list_filter = ()
    list_editable = ("is_active", "display_order")
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}
    fieldsets = (
        ("اطلاعات دسته بندی", {"fields": ("name", "slug", "description", "color", "is_active", "display_order")}),
    )


@admin.register(BlogTag)
class BlogTagAdmin(PersianAdminFormMixin, admin.ModelAdmin):
    list_display = ("name", "slug", "updated_at")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


class BlogCommentInline(admin.TabularInline):
    model = BlogComment
    extra = 0
    fields = ("name", "email", "body", "is_approved", "created_at")
    readonly_fields = ("created_at",)
    show_change_link = True


@admin.register(BlogPost)
class BlogPostAdmin(PersianAdminFormMixin, admin.ModelAdmin):
    list_display = ("title", "category", "status", "featured", "allow_comments", "published_at", "view_count")
    list_filter = ()
    list_editable = ("status", "featured", "allow_comments")
    search_fields = ("title", "slug", "subtitle", "excerpt", "content", "seo_title", "seo_description")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("tags",)
    autocomplete_fields = ("category", "author")
    readonly_fields = ("image_preview", "view_count", "created_at", "updated_at")
    inlines = (BlogCommentInline,)
    actions = ("publish_posts", "archive_posts")
    fieldsets = (
        ("محتوای مقاله", {"fields": ("title", "slug", "subtitle", "excerpt", "content")}),
        ("دسته بندی", {"fields": ("category", "tags", "author")}),
        ("تصویر", {"fields": ("hero_image", "image_preview", "hero_image_alt")}),
        ("انتشار", {"fields": ("status", "featured", "allow_comments", "reading_minutes", "published_at")}),
        ("سئو", {"fields": ("seo_title", "seo_description", "seo_keywords")}),
        ("آمار", {"fields": ("view_count", "created_at", "updated_at")}),
    )

    @admin.action(description="انتشار مقاله های انتخاب شده")
    def publish_posts(self, request, queryset):
        for post in queryset:
            post.status = BlogPost.Status.PUBLISHED
            post.save(update_fields=["status", "published_at", "slug", "seo_keywords", "updated_at"])
        self.message_user(request, f"{queryset.count()} مقاله منتشر شد.")

    @admin.action(description="آرشیو مقاله های انتخاب شده")
    def archive_posts(self, request, queryset):
        updated = queryset.update(status=BlogPost.Status.ARCHIVED)
        self.message_user(request, f"{updated} مقاله آرشیو شد.")

    @admin.display(description="پیش نمایش تصویر")
    def image_preview(self, obj: BlogPost | None) -> str:
        if not obj or not obj.hero_image:
            return "تصویری انتخاب نشده است."
        return format_html('<img src="{}" alt="" style="max-width:220px;border-radius:8px;" />', obj.hero_image.url)


@admin.register(BlogComment)
class BlogCommentAdmin(PersianAdminFormMixin, admin.ModelAdmin):
    list_display = ("name", "post", "is_approved", "created_at")
    list_filter = ()
    list_editable = ("is_approved",)
    search_fields = ("name", "email", "body", "post__title")
    autocomplete_fields = ("post", "parent")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("دیدگاه", {"fields": ("post", "parent", "name", "email", "body", "is_approved")}),
        ("زمان بندی", {"fields": ("created_at", "updated_at")}),
    )
