from rest_framework import serializers
from gateways.common import (_get_payment_reference_number)
from networkpg.models import NetworkTransaction
from networkpg.choices import PaymentStatus
from core.response_messages import YouPayResponse


class PaymentInitiationSerializer(serializers.Serializer):
    order_reference = serializers.CharField(max_length=200)
    amount = serializers.DecimalField(max_digits=12, decimal_places=5)
    currency = serializers.CharField(max_length=3, default='AED')
    customer_email = serializers.EmailField()
    customer_name = serializers.CharField(max_length=100)
    customer_phone = serializers.CharField(max_length=20)
    payment_reference = serializers.CharField(max_length=200, allow_null=True)
    redirect_url = serializers.URLField(required=False, allow_null=True)

    def validate(self, attrs):
        attrs["payment_reference"] = _get_payment_reference_number(
            attrs["order_reference"]
        )
        return attrs


class PaymentResponseSerializer(serializers.Serializer):
    payment_url = serializers.URLField()
    order_id = serializers.CharField()
    reference = serializers.CharField()
    status = serializers.CharField()


class NetworkTransactionSerializer(serializers.ModelSerializer):
    response_obj = YouPayResponse()

    class Meta:
        model = NetworkTransaction
        fields = '__all__'

    def save_ni_response(self, response):
        """
        Extracts card details and status from NI response and updates the instance.
        """
        payments = response.get('_embedded', {}).get('payment', [])
        if not payments:
            return self.instance

        active_payment = payments[0]
        success = False
        payment_method = active_payment.get('paymentMethod', {})
        pan = payment_method.get('pan', '')

        self.instance.card_bin = pan[:6] if pan else None
        self.instance.card_last4 = pan[-4:] if pan else None
        self.instance.card_scheme = payment_method.get('name')
        self.instance.card_holder_name = payment_method.get('cardholderName')
        self.instance.card_expiry_date = payment_method.get('expiry')
        self.instance.card_issuer_country = payment_method.get('issuingCountry')
        self.instance.card_type = payment_method.get('cardType')

        state = active_payment.get('state')
        if state:
            status_map = {
                "CAPTURED": PaymentStatus.CAPTURED,
                "AUTHORIZED": PaymentStatus.AUTHORIZED,
                "FAILED": PaymentStatus.FAILED,
                "STARTED": PaymentStatus.STARTED,
            }
            if state in status_map:
                self.instance.status = status_map[state]

            if state in ["CAPTURED", "AUTHORISED"]:
                self.instance.is_approved = True
                success = True

        self.instance.save()
        return self.response_structure(self.instance, success)

    def response_structure(self, instance, success):
        return_dict = {}
        if success:
            return_dict['is_success'] = True
            return_dict['is_redirect'] = True
            return_dict['code'] = self.response_obj.PAYMENT_SUCCESS
        else:
            return_dict['is_success'] = False
            return_dict['is_redirect'] = False
            return_dict['code'] = self.response_obj.PAYMENT_FAILED
        return_dict['redirect_url'] = instance.redirect_url
        return return_dict
