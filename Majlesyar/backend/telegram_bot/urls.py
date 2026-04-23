from django.urls import path

from .views import (
    TelegramBotAuditLogListAPIView,
    TelegramBotStateDetailAPIView,
    TelegramBotStateListAPIView,
    TelegramConfirmationListAPIView,
    TelegramOperatorDetailAPIView,
    TelegramOperatorListCreateAPIView,
    TelegramUpdateReceiptListAPIView,
)

urlpatterns = [
    path("admin/telegram/operators/", TelegramOperatorListCreateAPIView.as_view(), name="admin-telegram-operator-list-create"),
    path("admin/telegram/operators/<int:pk>/", TelegramOperatorDetailAPIView.as_view(), name="admin-telegram-operator-detail"),
    path("admin/telegram/audit-logs/", TelegramBotAuditLogListAPIView.as_view(), name="admin-telegram-audit-log-list"),
    path("admin/telegram/confirmations/", TelegramConfirmationListAPIView.as_view(), name="admin-telegram-confirmation-list"),
    path("admin/telegram/update-receipts/", TelegramUpdateReceiptListAPIView.as_view(), name="admin-telegram-update-receipt-list"),
    path("admin/telegram/states/", TelegramBotStateListAPIView.as_view(), name="admin-telegram-state-list"),
    path("admin/telegram/states/<int:pk>/", TelegramBotStateDetailAPIView.as_view(), name="admin-telegram-state-detail"),
]
