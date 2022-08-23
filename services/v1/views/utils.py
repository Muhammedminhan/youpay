from rest_framework import serializers


class PaymentSerializer(serializers.Serializer):
    product_code = serializers.CharField(required=True)
    payment_platform = serializers.CharField(required=True)
    ip = serializers.CharField(required=True)
    language = serializers.CharField(required=True)
    invoice_id = serializers.CharField(required=True)
    order_reference = serializers.CharField(required=True)


class PaymentRequestSerializer(serializers.Serializer):
    # payment = PaymentSerializer()
    # payment = serializers.CharField(required=True)
    api_client = serializers.CharField(required=True)
    
    