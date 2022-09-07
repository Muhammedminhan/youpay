from rest_framework import serializers

from checkoutpgclient.models import TransactionData


class TransactionDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransactionData
        fields = ['order_reference', 'amount', 'currency', 'customer_name',
                  'customer_email', 'idempotency_key',
                  'payment_reference', 'request_source', 'is_notification',
                  'approved', 'status', 'auth_code', 'response_summary',
                  'card_last4']
