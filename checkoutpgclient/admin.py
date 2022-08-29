from django.contrib import admin
from .models import TransactionData
from django.contrib import admin

from .models import TransactionData


class TransactionDataAdmin(admin.ModelAdmin):
    model = TransactionData

    list_display = ('payment_reference', 'invoice_id', 'currency',
                    'amount', 'status', 'is_flagged', 'customer_name',
                    'customer_email', 'card_last4', 'payment_method',
                    'created_on', 'modified_on')
    search_fields = ('customer_name', 'customer_email', 'payment_reference',
                     'invoice_id', 'card_last4')
    list_filter = ('approved', 'status', 'is_flagged', 'is_fraud',
                   'payment_method', 'payment_scheme')


admin.site.register(TransactionData, TransactionDataAdmin)
