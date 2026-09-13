from rest_framework import serializers

from .models import BlogCategory, BlogComment, BlogPost, BlogTag


class BlogCategorySerializer(serializers.ModelSerializer):
    post_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = BlogCategory
        fields = ("id", "name", "slug", "description", "color", "display_order", "post_count")


class BlogTagSerializer(serializers.ModelSerializer):
    post_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = BlogTag
        fields = ("id", "name", "slug", "post_count")


class BlogCommentSerializer(serializers.ModelSerializer):
    replies = serializers.SerializerMethodField()

    class Meta:
        model = BlogComment
        fields = ("id", "parent", "name", "body", "created_at", "replies")

    def get_replies(self, obj: BlogComment) -> list[dict]:
        replies = obj.replies.filter(is_approved=True).order_by("created_at")
        return BlogCommentSerializer(replies, many=True, context=self.context).data


class BlogCommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogComment
        fields = ("post", "parent", "name", "email", "body")
        read_only_fields = ("post",)

    def validate_name(self, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise serializers.ValidationError("نام الزامی است.")
        return cleaned

    def validate_body(self, value: str) -> str:
        cleaned = (value or "").strip()
        if len(cleaned) < 3:
            raise serializers.ValidationError("متن دیدگاه کوتاه است.")
        if len(cleaned) > 2000:
            raise serializers.ValidationError("متن دیدگاه نباید بیشتر از ۲۰۰۰ کاراکتر باشد.")
        return cleaned

    def validate_parent(self, value: BlogComment | None) -> BlogComment | None:
        post = self.context.get("post")
        if value and post and value.post_id != post.id:
            raise serializers.ValidationError("دیدگاه والد برای این مقاله نیست.")
        if value and not value.is_approved:
            raise serializers.ValidationError("امکان پاسخ به دیدگاه تایید نشده وجود ندارد.")
        if value and value.parent_id:
            raise serializers.ValidationError("پاسخ فقط برای دیدگاه های اصلی مجاز است.")
        return value


class BlogPostListSerializer(serializers.ModelSerializer):
    category = BlogCategorySerializer(read_only=True)
    tags = BlogTagSerializer(many=True, read_only=True)
    hero_image = serializers.SerializerMethodField()
    author_name = serializers.SerializerMethodField()
    uri = serializers.SerializerMethodField()

    class Meta:
        model = BlogPost
        fields = (
            "id",
            "title",
            "slug",
            "uri",
            "subtitle",
            "excerpt",
            "category",
            "tags",
            "author_name",
            "hero_image",
            "hero_image_alt",
            "featured",
            "reading_minutes",
            "view_count",
            "published_at",
            "seo_title",
            "seo_description",
            "seo_keywords",
        )

    def get_hero_image(self, obj: BlogPost) -> str | None:
        if not obj.hero_image:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.hero_image.url)
        return obj.hero_image.url

    def get_author_name(self, obj: BlogPost) -> str:
        if not obj.author:
            return ""
        full_name = obj.author.get_full_name()
        return full_name or obj.author.get_username()

    def get_uri(self, obj: BlogPost) -> str:
        return f"/blog/{obj.slug}"


class BlogPostDetailSerializer(BlogPostListSerializer):
    comments = serializers.SerializerMethodField()
    related_posts = serializers.SerializerMethodField()

    class Meta(BlogPostListSerializer.Meta):
        fields = BlogPostListSerializer.Meta.fields + (
            "content",
            "allow_comments",
            "comments",
            "related_posts",
        )

    def get_comments(self, obj: BlogPost) -> list[dict]:
        comments = obj.comments.filter(parent__isnull=True, is_approved=True).order_by("created_at")
        return BlogCommentSerializer(comments, many=True, context=self.context).data

    def get_related_posts(self, obj: BlogPost) -> list[dict]:
        queryset = BlogPost.objects.filter(status=BlogPost.Status.PUBLISHED).exclude(id=obj.id)
        if obj.category_id:
            queryset = queryset.filter(category_id=obj.category_id)
        related = queryset.select_related("category", "author").prefetch_related("tags")[:3]
        return BlogPostListSerializer(related, many=True, context=self.context).data


class BlogPostWriteSerializer(serializers.ModelSerializer):
    tag_ids = serializers.ListField(
        child=serializers.UUIDField(format="hex_verbose"),
        required=False,
        allow_empty=True,
        write_only=True,
    )

    class Meta:
        model = BlogPost
        fields = (
            "id",
            "title",
            "slug",
            "subtitle",
            "excerpt",
            "content",
            "category",
            "tag_ids",
            "author",
            "hero_image",
            "hero_image_alt",
            "status",
            "featured",
            "allow_comments",
            "reading_minutes",
            "seo_title",
            "seo_description",
            "seo_keywords",
            "published_at",
        )
        read_only_fields = ("id",)

    def validate_seo_keywords(self, value):
        if value in (None, ""):
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("کلمات کلیدی باید لیست باشند.")
        return [str(item).strip() for item in value if str(item).strip()]

    def validate_slug(self, value: str) -> str:
        return (value or "").strip()

    def validate_title(self, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise serializers.ValidationError("عنوان الزامی است.")
        return cleaned

    def _sync_tags(self, post: BlogPost, tag_ids):
        if tag_ids is not serializers.empty:
            post.tags.set(BlogTag.objects.filter(id__in=tag_ids))

    def create(self, validated_data: dict) -> BlogPost:
        tag_ids = validated_data.pop("tag_ids", serializers.empty)
        post = BlogPost.objects.create(**validated_data)
        self._sync_tags(post, tag_ids)
        return post

    def update(self, instance: BlogPost, validated_data: dict) -> BlogPost:
        tag_ids = validated_data.pop("tag_ids", serializers.empty)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        self._sync_tags(instance, tag_ids)
        return instance


class BlogCategoryWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogCategory
        fields = ("id", "name", "slug", "description", "color", "is_active", "display_order")
        read_only_fields = ("id",)


class BlogTagWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogTag
        fields = ("id", "name", "slug")
        read_only_fields = ("id",)


class BlogCommentAdminSerializer(serializers.ModelSerializer):
    post_title = serializers.CharField(source="post.title", read_only=True)

    class Meta:
        model = BlogComment
        fields = ("id", "post", "post_title", "parent", "name", "email", "body", "is_approved", "created_at")
