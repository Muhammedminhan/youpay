from django.contrib import admin
from django.contrib import messages

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
    actions = ['refund_payment']

    def refund_payment(self, request, queryset):
        """
        It will process the refund for the selected captured payment
        """
        payment_status = queryset.values_list('payment_status', flat=True)

        if all(status == 'captured' for status in payment_status):
            messages.info(request, "Refund request initiated, "
                                   "It may take 3  to 5 minutes "
                                   "to reflect on youpay portal")
        else:
            messages.error(request,
                           "Please select only captured payments")

    refund_payment.short_description = "Payment Refund"


admin.site.register(AmazonPGTransactionData, AmazonPGTransactionDataAdmin)
