from django.db.models import Q
from rest_framework import generics

from .models import BuilderItem, Category, Product
from .serializers import BuilderItemSerializer, CategorySerializer, ProductSerializer


class CategoryListAPIView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class ProductListAPIView(generics.ListAPIView):
    serializer_class = ProductSerializer

    def get_queryset(self):
        queryset = Product.objects.prefetch_related("categories").all()

        category_id = self.request.query_params.get("category")
        if category_id:
            queryset = queryset.filter(categories__id=category_id)

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
                | Q(description__icontains=search)
                | Q(contents__icontains=search)
            )

        return queryset.distinct()


class ProductDetailAPIView(generics.RetrieveAPIView):
    queryset = Product.objects.prefetch_related("categories").all()
    serializer_class = ProductSerializer
    lookup_field = "id"


class BuilderItemListAPIView(generics.ListAPIView):
    queryset = BuilderItem.objects.all()
    serializer_class = BuilderItemSerializer

# Create your views here.
