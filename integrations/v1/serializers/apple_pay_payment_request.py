from rest_framework import serializers

from payments.models import YouPayTransactionData


class ApplepayPaymentDataSerializer(serializers.ModelSerializer):

    class Meta:
        model = YouPayTransactionData
        fields = [
            'transaction_id',
            'amount',
            'currency',
            'invoice_id',
            'order_reference',
            'success_url',
            'failure_url',
            'cancel_url',
            'verify_url',
            'amount',
            'ip',
            'customer_email',
            'customer_name',
        ]
