from django.urls import path

from .views import (
    AdminBlogCategoryDetailAPIView,
    AdminBlogCategoryListCreateAPIView,
    AdminBlogCommentDetailAPIView,
    AdminBlogCommentListCreateAPIView,
    AdminBlogPostDetailAPIView,
    AdminBlogPostListCreateAPIView,
    AdminBlogTagDetailAPIView,
    AdminBlogTagListCreateAPIView,
    BlogCategoryListAPIView,
    BlogCommentCreateAPIView,
    BlogPostDetailAPIView,
    BlogPostListAPIView,
    BlogTagListAPIView,
)

urlpatterns = [
    path("blog/categories/", BlogCategoryListAPIView.as_view(), name="blog-category-list"),
    path("blog/tags/", BlogTagListAPIView.as_view(), name="blog-tag-list"),
    path("blog/posts/", BlogPostListAPIView.as_view(), name="blog-post-list"),
    path("blog/posts/<str:lookup>/", BlogPostDetailAPIView.as_view(), name="blog-post-detail"),
    path("blog/posts/<str:lookup>/comments/", BlogCommentCreateAPIView.as_view(), name="blog-comment-create"),
    path("admin/blog/categories/", AdminBlogCategoryListCreateAPIView.as_view(), name="admin-blog-category-list-create"),
    path("admin/blog/categories/<uuid:id>/", AdminBlogCategoryDetailAPIView.as_view(), name="admin-blog-category-detail"),
    path("admin/blog/tags/", AdminBlogTagListCreateAPIView.as_view(), name="admin-blog-tag-list-create"),
    path("admin/blog/tags/<uuid:id>/", AdminBlogTagDetailAPIView.as_view(), name="admin-blog-tag-detail"),
    path("admin/blog/posts/", AdminBlogPostListCreateAPIView.as_view(), name="admin-blog-post-list-create"),
    path("admin/blog/posts/<uuid:id>/", AdminBlogPostDetailAPIView.as_view(), name="admin-blog-post-detail"),
    path("admin/blog/comments/", AdminBlogCommentListCreateAPIView.as_view(), name="admin-blog-comment-list-create"),
    path("admin/blog/comments/<uuid:id>/", AdminBlogCommentDetailAPIView.as_view(), name="admin-blog-comment-detail"),
]
