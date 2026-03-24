from django.contrib import admin
from gateways.tpay.models import TPayTransaction, TPayWebhookLog


class TPayTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'tpay_transaction_id', 'payment_reference', 'status',
        'amount', 'currency', 'msisdn', 'operator_code',
        'created_at'
    )
    list_filter = ('status', 'currency', 'operator_code')
    search_fields = (
        'tpay_transaction_id', 'payment_reference', 'msisdn'
    )
    readonly_fields = (
        'raw_response', 'created_at', 'updated_at',
        'youpay_transaction'
    )
    ordering = ('-created_at',)

    fieldsets = (
        ('Identifiers', {
            'fields': (
                'tpay_transaction_id', 'payment_reference',
                'status', 'youpay_transaction'
            )
        }),
        ('Payment Details', {
            'fields': (
                'amount', 'currency', 'msisdn',
                'operator_code', 'payment_date'
            )
        }),
        ('Product Info', {
            'fields': ('product_catalog',)
        }),
        ('Raw Data & Logs', {
            'fields': ('raw_response',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


class TPayWebhookLogAdmin(admin.ModelAdmin):
    list_display = (
        'order_info', 'payment_transaction_status_code', 'transaction_id',
        'msisdn', 'amount', 'currency_code', 'created_at'
    )
    list_filter = (
        'payment_transaction_status_code', 'currency_code',
        'payment_provider_code'
    )
    search_fields = (
        'transaction_id', 'order_info', 'msisdn',
        'product_id', 'digest'
    )
    readonly_fields = ('created_at', 'payload')
    ordering = ('-created_at',)

    fieldsets = (
        ('Webhook Event', {
            'fields': ('action', 'payment_transaction_status_code', 'digest')
        }),
        ('Transaction Identifiers', {
            'fields': ('transaction_id', 'order_info', 'payment_provider_code')
        }),
        ('Customer & Payment', {
            'fields': ('msisdn', 'amount', 'currency_code', 'payment_date')
        }),
        ('Product Details', {
            'fields': ('product_catalog_name', 'product_id')
        }),
        ('Technical Data', {
            'fields': ('payload',)
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )

admin.site.register(TPayTransaction, TPayTransactionAdmin)
admin.site.register(TPayWebhookLog, TPayWebhookLogAdmin)
