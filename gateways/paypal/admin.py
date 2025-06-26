from django.contrib import admin

from core.admin import AdminAbstract
from gateways.paypal.models import (PaymentAccessToken, PaypalTransaction,
                                    PayPalWebhookLog)


class PaymentAccessTokenAdmin(AdminAbstract):
    list_display = ('access_token', 'created_at')
    readonly_fields = ('access_token', 'created_at')


class PaypalTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'order_id', 'payment_reference', 'status', 'amount', 'currency',
        'payer_id', 'created_at', 'updated_at',
    )
    list_filter = ('status', 'currency', 'created_at')
    search_fields = ('order_id', 'payment_reference', 'payer_id',
                     'tracking_id_stc', 'sender_youpay_account_id',
                     )
    readonly_fields = ('raw_response', 'created_at', 'updated_at')
    ordering = ('-created_at',)

    fieldsets = (
        ('Identifiers', {
            'fields': (
                'order_id', 'payment_reference', 'status', 'capture_id',
                'refund_id', 'payer_id',
            )
        }),
        ('Amounts & Fees', {
            'fields': (
                'amount', 'currency', 'paypal_fee', 'net_amount',
                'exchange_rate', 'receivable_amount',
                'receivable_amount_currency_code',
            )
        }),
        ('STC & Metadata', {
            'fields': (
                'tracking_id_stc', 'sender_youpay_account_id',
            )
        }),
        ('Debug & Logs', {
            'fields': (
                'debug_id', 'error_message', 'raw_response',
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


class PayPalWebhookLogAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_id", "event_type", "order_id", "status",
        "capture_status", "amount_value",
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
                "payment_reference", "refund_id")
        }),
        ("Payer Details", {
            "fields": ("payer_id", "payer_email", "payer_name")
        }),
        ("Capture Details", {
            "fields": ("capture_id", "capture_status")
        }),
        ("Amount Details", {
            "fields": (
                "amount_value", "amount_currency", "paypal_fee", "net_amount",
                "total_refunded_amount", "gross_amount")
        }),
        ("Exchange Details", {
            "fields": (
                "exchange_rate", "source_currency", "target_currency",
                "converted_amount", "payable_or_receivable_amount",
                "payable_or_receivable_currency_code"
            )
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
