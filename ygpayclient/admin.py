from django.contrib import admin
from .models import YGPayClientTransactionData


class YGPayClientTransactionDataAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'invoice_id', 'api_client', 'amount',
                    'currency', 'customer_email', 'payment_gateway',
                    'payment_status', 'created_on', 'modified_on')
    search_fields = ('transaction_id', 'invoice_id', 'api_client',
                     'customer_email',)
    list_filter = ('created_on', 'payment_status', 'api_client',
                   'payment_gateway', 'currency')


admin.site.register(YGPayClientTransactionData,
                    YGPayClientTransactionDataAdmin)
