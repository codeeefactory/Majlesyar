from django.urls import path

from .views import (
    BuilderItemListAPIView,
    CategoryListAPIView,
    ProductDetailAPIView,
    ProductListAPIView,
)

urlpatterns = [
    path("categories/", CategoryListAPIView.as_view(), name="category-list"),
    path("products/", ProductListAPIView.as_view(), name="product-list"),
    path("products/<uuid:id>/", ProductDetailAPIView.as_view(), name="product-detail"),
    path("builder-items/", BuilderItemListAPIView.as_view(), name="builder-item-list"),
]
