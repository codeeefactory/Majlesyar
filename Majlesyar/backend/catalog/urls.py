from django.urls import path

from .views import (
    AdminCategoryDetailAPIView,
    AdminCategoryListCreateAPIView,
    AdminProductDetailAPIView,
    AdminProductListCreateAPIView,
    BuilderItemListAPIView,
    CategoryListAPIView,
    ProductDetailAPIView,
    ProductListAPIView,
    TagListAPIView,
)

urlpatterns = [
    path("categories/", CategoryListAPIView.as_view(), name="category-list"),
    path("tags/", TagListAPIView.as_view(), name="tag-list"),
    path("products/", ProductListAPIView.as_view(), name="product-list"),
    path("products/<str:lookup>/", ProductDetailAPIView.as_view(), name="product-detail"),
    path("builder-items/", BuilderItemListAPIView.as_view(), name="builder-item-list"),
    path("admin/categories/", AdminCategoryListCreateAPIView.as_view(), name="admin-category-list-create"),
    path("admin/categories/<uuid:id>/", AdminCategoryDetailAPIView.as_view(), name="admin-category-detail"),
    path("admin/products/", AdminProductListCreateAPIView.as_view(), name="admin-product-list-create"),
    path("admin/products/<uuid:id>/", AdminProductDetailAPIView.as_view(), name="admin-product-detail"),
]
