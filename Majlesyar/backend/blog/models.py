import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from catalog.image_utils import image_extension_validator


class BlogCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name="شناسه")
    name = models.CharField(max_length=140, verbose_name="نام دسته بندی")
    slug = models.SlugField(max_length=160, unique=True, verbose_name="اسلاگ")
    description = models.TextField(blank=True, default="", verbose_name="توضیحات")
    color = models.CharField(max_length=64, blank=True, default="", verbose_name="رنگ")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    display_order = models.PositiveIntegerField(default=100, validators=[MinValueValidator(1)], verbose_name="ترتیب نمایش")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین بروزرسانی")

    class Meta:
        ordering = ["display_order", "name"]
        indexes = [
            models.Index(fields=["is_active", "display_order"]),
        ]
        verbose_name = "دسته بندی وبلاگ"
        verbose_name_plural = "دسته بندی های وبلاگ"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        base_slug = slugify((self.slug or self.name or "").strip()) or f"category-{str(self.id)[:8]}"
        candidate = base_slug
        suffix = 2
        while BlogCategory.objects.exclude(pk=self.pk).filter(slug=candidate).exists():
            candidate = f"{base_slug}-{suffix}"
            suffix += 1
        self.slug = candidate
        super().save(*args, **kwargs)


class BlogTag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name="شناسه")
    name = models.CharField(max_length=120, verbose_name="نام تگ")
    slug = models.SlugField(max_length=140, unique=True, verbose_name="اسلاگ")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین بروزرسانی")

    class Meta:
        ordering = ["name"]
        verbose_name = "تگ وبلاگ"
        verbose_name_plural = "تگ های وبلاگ"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        base_slug = slugify((self.slug or self.name or "").strip()) or f"tag-{str(self.id)[:8]}"
        candidate = base_slug
        suffix = 2
        while BlogTag.objects.exclude(pk=self.pk).filter(slug=candidate).exists():
            candidate = f"{base_slug}-{suffix}"
            suffix += 1
        self.slug = candidate
        super().save(*args, **kwargs)


class BlogPost(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "پیش نویس"
        PUBLISHED = "published", "منتشر شده"
        ARCHIVED = "archived", "آرشیو شده"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name="شناسه")
    title = models.CharField(max_length=220, verbose_name="عنوان")
    slug = models.SlugField(max_length=220, unique=True, blank=True, verbose_name="اسلاگ")
    subtitle = models.CharField(max_length=260, blank=True, default="", verbose_name="زیرعنوان")
    excerpt = models.TextField(blank=True, default="", verbose_name="خلاصه")
    content = models.TextField(verbose_name="متن مقاله")
    category = models.ForeignKey(
        BlogCategory,
        on_delete=models.SET_NULL,
        related_name="posts",
        null=True,
        blank=True,
        verbose_name="دسته بندی",
    )
    tags = models.ManyToManyField(BlogTag, related_name="posts", blank=True, verbose_name="تگ ها")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="blog_posts",
        null=True,
        blank=True,
        verbose_name="نویسنده",
    )
    hero_image = models.ImageField(
        upload_to="blog/",
        blank=True,
        null=True,
        validators=[image_extension_validator],
        verbose_name="تصویر شاخص",
    )
    hero_image_alt = models.CharField(max_length=255, blank=True, default="", verbose_name="متن جایگزین تصویر")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, verbose_name="وضعیت")
    featured = models.BooleanField(default=False, verbose_name="ویژه")
    allow_comments = models.BooleanField(default=True, verbose_name="امکان ثبت دیدگاه")
    reading_minutes = models.PositiveSmallIntegerField(default=3, validators=[MinValueValidator(1), MaxValueValidator(60)], verbose_name="زمان مطالعه")
    view_count = models.PositiveIntegerField(default=0, verbose_name="تعداد بازدید")
    seo_title = models.CharField(max_length=260, blank=True, default="", verbose_name="عنوان سئو")
    seo_description = models.TextField(blank=True, default="", verbose_name="توضیحات سئو")
    seo_keywords = models.JSONField(default=list, blank=True, verbose_name="کلمات کلیدی سئو")
    published_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان انتشار")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین بروزرسانی")

    class Meta:
        ordering = ["-featured", "-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["status", "published_at"]),
            models.Index(fields=["featured", "published_at"]),
            models.Index(fields=["category", "status", "published_at"]),
        ]
        verbose_name = "مقاله وبلاگ"
        verbose_name_plural = "مقاله های وبلاگ"

    def __str__(self) -> str:
        return self.title

    @property
    def is_published(self) -> bool:
        if self.status != self.Status.PUBLISHED:
            return False
        return self.published_at is None or self.published_at <= timezone.now()

    def save(self, *args, **kwargs):
        base_slug = slugify((self.slug or self.title or "").strip()) or f"post-{str(self.id)[:8]}"
        candidate = base_slug
        suffix = 2
        while BlogPost.objects.exclude(pk=self.pk).filter(slug=candidate).exists():
            candidate = f"{base_slug}-{suffix}"
            suffix += 1
        self.slug = candidate

        if self.status == self.Status.PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()
        if not isinstance(self.seo_keywords, list):
            self.seo_keywords = []

        super().save(*args, **kwargs)


class BlogComment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name="شناسه")
    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name="comments", verbose_name="مقاله")
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="replies",
        null=True,
        blank=True,
        verbose_name="پاسخ به",
    )
    name = models.CharField(max_length=120, verbose_name="نام")
    email = models.EmailField(blank=True, default="", verbose_name="ایمیل")
    body = models.TextField(verbose_name="متن دیدگاه")
    is_approved = models.BooleanField(default=False, verbose_name="تایید شده")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین بروزرسانی")

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["post", "is_approved", "parent", "created_at"]),
        ]
        verbose_name = "دیدگاه وبلاگ"
        verbose_name_plural = "دیدگاه های وبلاگ"

    def __str__(self) -> str:
        return f"{self.name} - {self.post.title}"
