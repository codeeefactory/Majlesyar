from django.urls import path

from .views import (
    ClientProfileDetailAPIView,
    ClientProfileListCreateAPIView,
    DashboardSummaryAPIView,
    DesktopBootstrapAPIView,
    InvoiceDetailAPIView,
    InvoiceListCreateAPIView,
    OfflineSessionImportAPIView,
    OperationsAuditLogListAPIView,
    ReminderListAPIView,
    SendReminderAPIView,
    SmsLogListAPIView,
    SmsTemplateDetailAPIView,
    SmsTemplateListCreateAPIView,
    StaffUserDetailAPIView,
    StaffUserListCreateAPIView,
)


urlpatterns = [
    path("admin/staff/", StaffUserListCreateAPIView.as_view(), name="admin-staff-list-create"),
    path("admin/staff/<int:pk>/", StaffUserDetailAPIView.as_view(), name="admin-staff-detail"),
    path("admin/clients/", ClientProfileListCreateAPIView.as_view(), name="admin-client-list-create"),
    path("admin/clients/<uuid:pk>/", ClientProfileDetailAPIView.as_view(), name="admin-client-detail"),
    path("admin/clients/<uuid:client_id>/send-reminder/", SendReminderAPIView.as_view(), name="admin-client-send-reminder"),
    path("admin/invoices/", InvoiceListCreateAPIView.as_view(), name="admin-invoice-list-create"),
    path("admin/invoices/<uuid:pk>/", InvoiceDetailAPIView.as_view(), name="admin-invoice-detail"),
    path("admin/sms-templates/", SmsTemplateListCreateAPIView.as_view(), name="admin-sms-template-list-create"),
    path("admin/sms-templates/<uuid:pk>/", SmsTemplateDetailAPIView.as_view(), name="admin-sms-template-detail"),
    path("admin/sms-logs/", SmsLogListAPIView.as_view(), name="admin-sms-log-list"),
    path("admin/reminders/", ReminderListAPIView.as_view(), name="admin-reminder-list"),
    path("admin/dashboard/", DashboardSummaryAPIView.as_view(), name="admin-dashboard-summary"),
    path("admin/bootstrap/", DesktopBootstrapAPIView.as_view(), name="admin-desktop-bootstrap"),
    path("admin/offline-session/import/", OfflineSessionImportAPIView.as_view(), name="admin-offline-session-import"),
    path("admin/audit-log/", OperationsAuditLogListAPIView.as_view(), name="admin-operations-audit-log"),
]
