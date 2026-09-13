def order_status_choices():
    from orders.models import Order

    return Order.Status.choices


def invoice_status_choices():
    from operations.models import Invoice

    return Invoice.Status.choices


def sms_status_choices():
    from operations.models import SmsLog

    return SmsLog.Status.choices


def telegram_update_status_choices():
    from telegram_bot.models import TelegramUpdateReceipt

    return TelegramUpdateReceipt.Status.choices


def telegram_audit_status_choices():
    from telegram_bot.models import TelegramBotAuditLog

    return TelegramBotAuditLog.Status.choices


def blog_post_status_choices():
    from blog.models import BlogPost

    return BlogPost.Status.choices
