from rest_framework import serializers

from gateways.common import (unique_token_generator)
from networkpg.models import NetworkTransaction
from networkpg.choices import PaymentStatus
from core.response_messages import YouPayResponse
from core.utils import get_display_program, get_redirect_url


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
        invoice_id = self.initial_data.get("invoice_id")
        attrs["payment_reference"] = (
            self._generate_ni_payment_order_reference(invoice_id)
        )
        return attrs

    def _generate_ni_payment_order_reference(self, invoice_id):
        """
        Generates a unique order reference for Network International.
        """
        return (
            f"Gift-Invoice-{invoice_id}-"
            f"{unique_token_generator(4)}"
        )


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

        state = active_payment.get('state')
        if state:
            status_map = {
                "CAPTURED": PaymentStatus.CAPTURED,
                "AUTHORIZED": PaymentStatus.AUTHORIZED,
                "FAILED": PaymentStatus.DECLINED,
                "INITIATED": PaymentStatus.INITIATED,
                "DECLINED": PaymentStatus.DECLINED,
                "THREE_DS_NOT_AUTHENTICATED": PaymentStatus.DECLINED,
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
        transaction_id = instance.youpay_transaction.transaction_id
        if success:
            return_dict['is_success'] = True

            return_dict['platform'] = instance.youpay_transaction.platform.upper()
            return_dict['country_code'] = instance.youpay_transaction.country_code
            return_dict['is_guest'] = instance.youpay_transaction.is_guest
            return_dict['program'] = get_display_program(instance.youpay_transaction.api_client)
            return_dict['retry_count'] = instance.youpay_transaction.retry_count
            return_dict['payment_method'] = "network_card"
            return_dict['code'] = self.response_obj.PAYMENT_SUCCESS
        else:
            return_dict['is_success'] = False
            return_dict['code'] = self.response_obj.PAYMENT_FAILED
        return_dict['is_redirect'] = True
        return_dict['redirect_url'] = get_redirect_url(instance.redirect_url,
                                                       str(transaction_id))
        return return_dict
