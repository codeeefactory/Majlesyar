from django.urls import path

from .views import (
    AdminOrderListAPIView,
    AdminOrderNoteCreateAPIView,
    AdminOrderStatusUpdateAPIView,
    PublicOrderCreateAPIView,
    PublicOrderRetrieveAPIView,
)

urlpatterns = [
    path("orders/", PublicOrderCreateAPIView.as_view(), name="order-create"),
    path("orders/<str:public_id>/", PublicOrderRetrieveAPIView.as_view(), name="order-detail"),
    path("admin/orders/", AdminOrderListAPIView.as_view(), name="admin-order-list"),
    path(
        "admin/orders/<str:public_id>/",
        AdminOrderStatusUpdateAPIView.as_view(),
        name="admin-order-status-update",
    ),
    path(
        "admin/orders/<str:public_id>/notes/",
        AdminOrderNoteCreateAPIView.as_view(),
        name="admin-order-note-create",
    ),
]
