from django.contrib import admin

from .models import AmazonPGTransactionData

# Register your models here.


class AmazonPGTransactionDataAdmin(admin.ModelAdmin):
    model = AmazonPGTransactionData

    list_display = ('payment_reference', 'invoice_id', 'currency',
                    'amount', 'payment_status', 'apg_payment_status',
                    'customer_name', 'customer_email', 'card_last4',
                    'created_at', 'updated_at')
    search_fields = ('customer_name', 'customer_email', 'payment_reference',
                     'invoice_id', 'card_last4')
    list_filter = ('apg_payment_status', 'payment_status')


admin.site.register(AmazonPGTransactionData, AmazonPGTransactionDataAdmin)
