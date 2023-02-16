from rest_framework import serializers

from payments.models import YouPayTransactionData


class YouPayTransactionDataSerializer(serializers.ModelSerializer):
    session_id = serializers.CharField(max_length=255, required=True)

    class Meta:
        model = YouPayTransactionData
        fields = '__all__'

class ApplepayPaymentDataSerializer(serializers.ModelSerializer):
    session_id = serializers.CharField(max_length=255, required=True)

    class Meta:
        model = YouPayTransactionData
        fields = [
            'session_id',
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