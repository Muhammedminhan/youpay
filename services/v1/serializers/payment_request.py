from rest_framework import serializers

from core.utils import decrypt_string
from services.models import PaymentRequestData


def amount_validator(amount):
    if amount < 0:
        raise serializers.ValidationError("Amount must be positive")
    return amount


class PaymentRequestDataSerializer(serializers.ModelSerializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=4,
                                      validators=[amount_validator])

    class Meta:
        model = PaymentRequestData
        fields = '__all__'


class PaymentVerifyDataSerializer(serializers.Serializer):
    transaction_id = serializers.CharField()
    invoice_id = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=4,
                                      validators=[amount_validator])
    currency = serializers.CharField()


class OTPSerializer(serializers.Serializer):
    transaction_id = serializers.CharField(required=True)
    mobile_number = serializers.CharField(required=True)

    @property
    def transaction_obj(self):
        transaction_id = self.validated_data.get('transaction_id')
        from services.v1.views.common import YouPayTransactionCRUD
        obj = YouPayTransactionCRUD()
        transaction_obj = obj.get_youpay_transaction_data(
            decrypt_string(transaction_id))
        if transaction_obj:
            return transaction_obj
        else:
            raise serializers.ValidationError((
                "OTPSerializer : Transaction not found with ID"
                " {}".format(transaction_id)))
