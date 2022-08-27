from django.contrib import admin

from payments.models import YGPayTransactionData


class YGPayTransactionDataAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'amount', 'currency', 'customer_email',
                    'payment_status', 'invoice_id', 'created_at',
                    'api_client', 'payment_gateway', 'updated_at',)
    readonly_fields = ('created_at', 'updated_at', 'customer_email'
                       , 'customer_phone')
    search_fields = ('transaction_id', 'customer_email', 'invoice_id',
                     'payment_reference', 'order_reference')
    list_filter = ('created_at', 'payment_status', 'api_client',
                   'payment_gateway', 'currency')


admin.site.register(YGPayTransactionData, YGPayTransactionDataAdmin)
