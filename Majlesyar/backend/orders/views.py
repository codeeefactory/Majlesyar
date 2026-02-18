from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Order, OrderNote
from .permissions import IsStaffUser
from .serializers import (
    OrderCreateSerializer,
    OrderNoteCreateSerializer,
    OrderNoteSerializer,
    OrderSerializer,
    OrderStatusUpdateSerializer,
)


class PublicOrderCreateAPIView(generics.CreateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderCreateSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        response_serializer = OrderSerializer(order, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class PublicOrderRetrieveAPIView(generics.RetrieveAPIView):
    serializer_class = OrderSerializer
    permission_classes = [AllowAny]
    lookup_field = "public_id"

    def get_queryset(self):
        return Order.objects.prefetch_related("items", "notes").all()

    def get_object(self):
        queryset = self.get_queryset()
        public_id = self.kwargs["public_id"].upper()
        return get_object_or_404(queryset, public_id=public_id)


class AdminOrderListAPIView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsStaffUser]

    def get_queryset(self):
        queryset = Order.objects.prefetch_related("items", "notes").all()
        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(public_id__icontains=search)
                | Q(customer_name__icontains=search)
                | Q(customer_phone__icontains=search)
            )
        return queryset


class AdminOrderStatusUpdateAPIView(generics.GenericAPIView):
    serializer_class = OrderStatusUpdateSerializer
    permission_classes = [IsStaffUser]

    def get_queryset(self):
        return Order.objects.prefetch_related("items", "notes").all()

    def patch(self, request, public_id: str):
        order = get_object_or_404(self.get_queryset(), public_id=public_id.upper())
        serializer = self.get_serializer(order, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(OrderSerializer(order, context={"request": request}).data)


class AdminOrderNoteCreateAPIView(generics.GenericAPIView):
    serializer_class = OrderNoteCreateSerializer
    permission_classes = [IsStaffUser]

    def post(self, request, public_id: str):
        order = get_object_or_404(Order, public_id=public_id.upper())
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        note = OrderNote.objects.create(
            order=order,
            note=serializer.validated_data["note"],
            created_by=request.user,
        )
        return Response(
            OrderNoteSerializer(note, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

# Create your views here.
