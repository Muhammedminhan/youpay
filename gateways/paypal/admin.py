from django.contrib import admin

from core.admin import AdminAbstract
from gateways.paypal.models import (PaymentAccessToken, PaypalTransaction,
                                    PayPalWebhookLog)


class PaymentAccessTokenAdmin(AdminAbstract):
    list_display = ('access_token', 'created_at')
    readonly_fields = ('access_token', 'created_at')


class PaypalTransactionAdmin(AdminAbstract):
    list_display = (
        'payment_reference', 'order_id', 'currency', 'amount', 'status',
        'created_at')
    search_fields = ('payment_reference', 'order_id', 'currency', 'amount')
    list_filter = ('status', 'currency')


class PayPalWebhookLogAdmin(admin.ModelAdmin):
    list_display = (
        "event_type", "order_id", "status", "capture_status", "amount_value",
        "amount_currency", "payer_email", "created_at",
    )
    readonly_fields = ("created_at",)

    search_fields = (
        "event_id", "event_type", "order_id", "capture_id", "payer_email",
        "invoice_id", "payment_reference",
    )

    list_filter = (
        "event_type", "status", "capture_status", "amount_currency",
    )

    fieldsets = (
        ("Event Info", {
            "fields": ("event_id", "event_type", "resource_type", "summary")
        }),
        ("Order Details", {
            "fields": (
                "order_id", "status", "intent", "invoice_id",
                "payment_reference")
        }),
        ("Payer Details", {
            "fields": ("payer_id", "payer_email", "payer_name")
        }),
        ("Capture Details", {
            "fields": ("capture_id", "capture_status")
        }),
        ("Amount Details", {
            "fields": (
                "amount_value", "amount_currency", "paypal_fee", "net_amount")
        }),
        ("Raw Payload", {
            "fields": ("payload",)
        }),
        ("Timestamps", {
            "fields": ("created_at",)
        }),
    )

admin.site.register(PaymentAccessToken, PaymentAccessTokenAdmin)
admin.site.register(PaypalTransaction, PaypalTransactionAdmin)
admin.site.register(PayPalWebhookLog, PayPalWebhookLogAdmin)
