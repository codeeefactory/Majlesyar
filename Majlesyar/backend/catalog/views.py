import uuid

from django.db.models import Q
from django.http import Http404
from rest_framework import generics
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from .models import BuilderItem, Category, Product, Tag
from .serializers import (
    BuilderItemSerializer,
    CategorySerializer,
    CategoryWriteSerializer,
    ProductSerializer,
    ProductWriteSerializer,
    TagSerializer,
)
from orders.permissions import IsStaffUser


class CategoryListAPIView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class TagListAPIView(generics.ListAPIView):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class ProductListAPIView(generics.ListAPIView):
    serializer_class = ProductSerializer

    def get_queryset(self):
        queryset = Product.objects.prefetch_related("categories", "tags").all()

        category_id = self.request.query_params.get("category")
        if category_id:
            queryset = queryset.filter(categories__id=category_id)

        tag_id = self.request.query_params.get("tag")
        if tag_id:
            queryset = queryset.filter(tags__id=tag_id)
        tag_slug = self.request.query_params.get("tag_slug")
        if tag_slug:
            queryset = queryset.filter(tags__slug=tag_slug)

        event_type = self.request.query_params.get("event_type")
        if event_type:
            queryset = queryset.filter(event_types__contains=[event_type])

        featured = self.request.query_params.get("featured")
        if featured is not None:
            queryset = queryset.filter(featured=featured.lower() == "true")

        available = self.request.query_params.get("available")
        if available is not None:
            queryset = queryset.filter(available=available.lower() == "true")

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(url_slug__icontains=search)
                | Q(description__icontains=search)
                | Q(contents__icontains=search)
                | Q(tags__name__icontains=search)
                | Q(tags__slug__icontains=search)
            )

        return queryset.distinct()


class ProductDetailAPIView(generics.RetrieveAPIView):
    queryset = Product.objects.prefetch_related("categories", "tags").all()
    serializer_class = ProductSerializer
    lookup_url_kwarg = "lookup"

    def get_object(self):
        queryset = self.get_queryset()
        lookup_value = str(self.kwargs.get(self.lookup_url_kwarg, "")).strip()
        if not lookup_value:
            raise Http404

        by_slug = queryset.filter(url_slug=lookup_value).first()
        if by_slug:
            return by_slug

        try:
            product_id = uuid.UUID(lookup_value)
        except (ValueError, TypeError):
            raise Http404 from None

        by_id = queryset.filter(id=product_id).first()
        if by_id:
            return by_id

        raise Http404


class BuilderItemListAPIView(generics.ListAPIView):
    queryset = BuilderItem.objects.all()
    serializer_class = BuilderItemSerializer


class AdminProductListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [IsStaffUser]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        queryset = Product.objects.prefetch_related("categories", "tags").all()

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(url_slug__icontains=search)
                | Q(description__icontains=search)
                | Q(contents__icontains=search)
                | Q(tags__name__icontains=search)
                | Q(tags__slug__icontains=search)
            )

        available = self.request.query_params.get("available")
        if available is not None:
            queryset = queryset.filter(available=available.lower() == "true")

        featured = self.request.query_params.get("featured")
        if featured is not None:
            queryset = queryset.filter(featured=featured.lower() == "true")

        category_id = self.request.query_params.get("category")
        if category_id:
            queryset = queryset.filter(categories__id=category_id)

        tag_id = self.request.query_params.get("tag")
        if tag_id:
            queryset = queryset.filter(tags__id=tag_id)
        tag_slug = self.request.query_params.get("tag_slug")
        if tag_slug:
            queryset = queryset.filter(tags__slug=tag_slug)

        return queryset.distinct()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ProductWriteSerializer
        return ProductSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        response_serializer = ProductSerializer(product, context={"request": request})
        headers = self.get_success_headers(response_serializer.data)
        return Response(response_serializer.data, status=201, headers=headers)


class AdminProductDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsStaffUser]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    lookup_field = "id"

    def get_queryset(self):
        return Product.objects.prefetch_related("categories", "tags").all()

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return ProductWriteSerializer
        return ProductSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        response_serializer = ProductSerializer(product, context={"request": request})
        return Response(response_serializer.data)


class AdminCategoryListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [IsStaffUser]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    queryset = Category.objects.all()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CategoryWriteSerializer
        return CategorySerializer


class AdminCategoryDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsStaffUser]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    queryset = Category.objects.all()
    lookup_field = "id"

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return CategoryWriteSerializer
        return CategorySerializer
