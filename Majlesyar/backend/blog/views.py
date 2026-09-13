from django.db.models import Count, F, Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.permissions import IsStaffUser

from .models import BlogCategory, BlogComment, BlogPost, BlogTag
from .serializers import (
    BlogCategorySerializer,
    BlogCategoryWriteSerializer,
    BlogCommentAdminSerializer,
    BlogCommentCreateSerializer,
    BlogPostDetailSerializer,
    BlogPostListSerializer,
    BlogPostWriteSerializer,
    BlogTagSerializer,
    BlogTagWriteSerializer,
)


def published_posts_queryset():
    published_time_filter = Q(published_at__isnull=True) | Q(published_at__lte=timezone.now())
    return (
        BlogPost.objects.filter(status=BlogPost.Status.PUBLISHED)
        .filter(published_time_filter)
        .select_related("category", "author")
        .prefetch_related("tags")
    )


class BlogCategoryListAPIView(generics.ListAPIView):
    serializer_class = BlogCategorySerializer

    def get_queryset(self):
        published_time_filter = Q(posts__published_at__isnull=True) | Q(posts__published_at__lte=timezone.now())
        return (
            BlogCategory.objects.filter(is_active=True)
            .annotate(
                post_count=Count(
                    "posts",
                    filter=Q(posts__status=BlogPost.Status.PUBLISHED) & published_time_filter,
                )
            )
            .filter(post_count__gt=0)
        )


class BlogTagListAPIView(generics.ListAPIView):
    serializer_class = BlogTagSerializer

    def get_queryset(self):
        published_time_filter = Q(posts__published_at__isnull=True) | Q(posts__published_at__lte=timezone.now())
        return (
            BlogTag.objects.annotate(
                post_count=Count(
                    "posts",
                    filter=Q(posts__status=BlogPost.Status.PUBLISHED) & published_time_filter,
                )
            )
            .filter(post_count__gt=0)
            .order_by("name")
        )


class BlogPostListAPIView(generics.ListAPIView):
    serializer_class = BlogPostListSerializer

    def get_queryset(self):
        queryset = published_posts_queryset()
        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(Q(category__slug=category) | Q(category_id=category))

        tag = self.request.query_params.get("tag")
        if tag:
            queryset = queryset.filter(Q(tags__slug=tag) | Q(tags__id=tag))

        featured = self.request.query_params.get("featured")
        if featured is not None:
            queryset = queryset.filter(featured=featured.lower() == "true")

        search = (self.request.query_params.get("search") or "").strip()
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search)
                | Q(subtitle__icontains=search)
                | Q(excerpt__icontains=search)
                | Q(content__icontains=search)
                | Q(category__name__icontains=search)
                | Q(tags__name__icontains=search)
            )

        limit = self.request.query_params.get("limit")
        queryset = queryset.distinct()
        if limit:
            try:
                return queryset[: max(1, min(int(limit), 48))]
            except (TypeError, ValueError):
                return queryset
        return queryset


class BlogPostDetailAPIView(generics.RetrieveAPIView):
    serializer_class = BlogPostDetailSerializer
    lookup_url_kwarg = "lookup"

    def get_queryset(self):
        return published_posts_queryset()

    def get_object(self):
        lookup = str(self.kwargs.get(self.lookup_url_kwarg, "")).strip()
        queryset = self.get_queryset()
        post = queryset.filter(slug=lookup).first()
        if not post:
            try:
                post = queryset.filter(id=lookup).first()
            except (TypeError, ValueError):
                post = None
        if not post:
            raise Http404
        BlogPost.objects.filter(id=post.id).update(view_count=F("view_count") + 1)
        post.view_count += 1
        return post


class BlogCommentCreateAPIView(APIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = BlogCommentCreateSerializer

    def post(self, request, lookup: str):
        post = get_object_or_404(published_posts_queryset(), slug=lookup)
        if not post.allow_comments:
            return Response({"detail": "ثبت دیدگاه برای این مقاله غیرفعال است."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = BlogCommentCreateSerializer(data=request.data, context={"post": post})
        serializer.is_valid(raise_exception=True)
        serializer.save(post=post)
        return Response({"detail": "دیدگاه شما پس از تایید نمایش داده می شود."}, status=status.HTTP_201_CREATED)


class AdminBlogPostListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [IsStaffUser]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        queryset = BlogPost.objects.select_related("category", "author").prefetch_related("tags").all()
        search = (self.request.query_params.get("search") or "").strip()
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search)
                | Q(slug__icontains=search)
                | Q(excerpt__icontains=search)
                | Q(content__icontains=search)
            )
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset.distinct()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return BlogPostWriteSerializer
        return BlogPostListSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        post = serializer.save(author=serializer.validated_data.get("author") or request.user)
        response_serializer = BlogPostDetailSerializer(post, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class AdminBlogPostDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsStaffUser]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    queryset = BlogPost.objects.select_related("category", "author").prefetch_related("tags").all()
    lookup_field = "id"

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return BlogPostWriteSerializer
        return BlogPostDetailSerializer


class AdminBlogCategoryListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [IsStaffUser]

    def get_queryset(self):
        return BlogCategory.objects.annotate(post_count=Count("posts"))

    def get_serializer_class(self):
        if self.request.method == "POST":
            return BlogCategoryWriteSerializer
        return BlogCategorySerializer


class AdminBlogCategoryDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsStaffUser]
    queryset = BlogCategory.objects.all()
    lookup_field = "id"
    serializer_class = BlogCategoryWriteSerializer


class AdminBlogTagListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [IsStaffUser]

    def get_queryset(self):
        return BlogTag.objects.annotate(post_count=Count("posts"))

    def get_serializer_class(self):
        if self.request.method == "POST":
            return BlogTagWriteSerializer
        return BlogTagSerializer


class AdminBlogTagDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsStaffUser]
    queryset = BlogTag.objects.all()
    lookup_field = "id"
    serializer_class = BlogTagWriteSerializer


class AdminBlogCommentListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [IsStaffUser]
    queryset = BlogComment.objects.select_related("post", "parent").all()
    serializer_class = BlogCommentAdminSerializer


class AdminBlogCommentDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsStaffUser]
    queryset = BlogComment.objects.select_related("post", "parent").all()
    serializer_class = BlogCommentAdminSerializer
    lookup_field = "id"
