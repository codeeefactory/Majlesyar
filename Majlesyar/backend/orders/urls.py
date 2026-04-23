from django.urls import path

from .views import (
    AdminOrderDetailAPIView,
    AdminOrderListCreateAPIView,
    AdminOrderNoteCreateAPIView,
    AdminProductSalesReportAPIView,
    PublicOrderCreateAPIView,
    PublicOrderRetrieveAPIView,
)

urlpatterns = [
    path("orders/", PublicOrderCreateAPIView.as_view(), name="order-create"),
    path("orders/<str:public_id>/", PublicOrderRetrieveAPIView.as_view(), name="order-detail"),
    path("admin/orders/", AdminOrderListCreateAPIView.as_view(), name="admin-order-list"),
    path(
        "admin/orders/<str:public_id>/",
        AdminOrderDetailAPIView.as_view(),
        name="admin-order-status-update",
    ),
    path(
        "admin/orders/<str:public_id>/notes/",
        AdminOrderNoteCreateAPIView.as_view(),
        name="admin-order-note-create",
    ),
    path(
        "admin/reports/product-sales/",
        AdminProductSalesReportAPIView.as_view(),
        name="admin-product-sales-report",
    ),
]
