from django.contrib import admin
from .models import YGPayClientTransactionData


class YGPayClientTransactionDataAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'payment_reference', 'invoice_id',
                    'amount', 'currency', 'customer_email', 'payment_gateway',
                    'payment_status', 'created_on', 'modified_on')
    search_fields = ('transaction_id', 'invoice_id', 'customer_email',)
    list_filter = ('created_on', 'payment_status',
                   'payment_gateway', 'currency')


admin.site.register(YGPayClientTransactionData,
                    YGPayClientTransactionDataAdmin)
