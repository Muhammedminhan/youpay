from django.contrib import admin
from django.contrib import messages

from .models import AmazonPGTransactionData
from payments.models import YouPayTransactionData
from integrations.v1.gateway_clients.amazonpg import AmazonPGManager
from payments.constants import PAYMENT_STATUS_REFUNDED


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

    def get_transaction_data(self, payment_reference):
        try:
            transaction_obj = YouPayTransactionData.objects.get(
                payment_reference=payment_reference)
            return transaction_obj
        except YouPayTransactionData.DoesNotExist:
            return None

    def refund_payment(self, request, queryset):
        """
        It will process the refund for the selected captured payment
        """

        payment_status = queryset.values_list('payment_status', flat=True)
        lst_success_id = []
        lst_failed_id = []

        if all(status == 'captured' for status in payment_status):
            payment_reference = queryset.values_list('payment_reference')
            for payment_ref in payment_reference:
                payment_id = payment_ref[0]
                refund_data = {
                    "payment_reference": payment_id,
                    "transaction_obj": self.get_transaction_data(
                        payment_id
                    )
                }
                amazon_pay = AmazonPGManager()
                status, code = amazon_pay.payment_refund(refund_data)
                if status == PAYMENT_STATUS_REFUNDED:
                    lst_success_id.append(payment_id)
                else:
                    lst_failed_id.append(payment_id)

            if lst_success_id:
                message = ("Payment refund completed successfully for " +
                           ", ".join(lst_success_id))
                messages.info(request, message)
            if lst_failed_id:
                message = ("Payment refund failed for " +
                           ", ".join(lst_failed_id))
                messages.error(request, message)
        else:
            messages.error(request,
                           "Please select only captured payments")

    refund_payment.short_description = "Payment Refund"


admin.site.register(AmazonPGTransactionData, AmazonPGTransactionDataAdmin)
