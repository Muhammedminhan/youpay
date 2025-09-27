from rest_framework import serializers

from core.utils import decrypt_string


class QitafPaymentRequestSerializer(serializers.Serializer):
    invoice = serializers.SerializerMethodField()
    platform = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    customer_email = serializers.SerializerMethodField()
    request_id = serializers.SerializerMethodField()
    MSISDN = serializers.SerializerMethodField()
    language_code = serializers.SerializerMethodField()
    mobile_number = serializers.SerializerMethodField()
    reference_id = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()
    currency = serializers.SerializerMethodField()
    is_full_redemption = serializers.SerializerMethodField()
    amount_in_aed = serializers.SerializerMethodField()

    def get_invoice(self, data):
        return data.get('transaction_obj').invoice_id

    def get_platform(self, data):
        return data.get('transaction_obj').platform

    def get_customer_name(self, data):
        return data.get('transaction_obj').customer_name

    def get_customer_email(self, data):
        return data.get('transaction_obj').customer_email

    def get_request_id(self, data):
        return data.get('transaction_obj').qitaf_request_id

    def get_MSISDN(self, data):
        return data.get('transaction_obj').qitaf_phone_number

    def get_language_code(self, data):
        return data.get('transaction_obj').language

    def get_mobile_number(self, data):
        return data.get('transaction_obj').customer_phone

    def get_reference_id(self, data):
        return data.get('transaction_obj').payment_reference

    def get_amount(self, data):
        """
        as per PRD : the base price will be redeemed and no additional charges
        link : https://yougotagift.atlassian.net/wiki/spaces/YPRD/pages/2294808578/Qitaf+charges
        """
        return str(data.get('transaction_obj').base_amount)

    def get_currency(self, data):
        return data.get('transaction_obj').currency

    def get_is_full_redemption(self, data):
        return data.get('transaction_obj').is_full_redemption

    def get_amount_in_aed(self, data):
        return str(data.get('transaction_obj').amount_in_aed)


class QitafRedemptionSerializer(serializers.Serializer):
    selected_amount = serializers.SerializerMethodField()
    checkout_amount = serializers.SerializerMethodField()
    pin_number = serializers.SerializerMethodField()
    is_save_user_token = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    token = serializers.SerializerMethodField()
    cvv = serializers.SerializerMethodField()
    token_type = serializers.SerializerMethodField()
    session_id = serializers.SerializerMethodField()
    session_data = serializers.SerializerMethodField()

    def get_selected_amount(self, data):
        data = self.context.get('request').data
        return data.get('selected_amount')

    def get_checkout_amount(self, data):
        data = self.context.get('request').data
        return data.get('checkout_amount')

    def get_pin_number(self, data):
        data = self.context.get('request').data
        return data.get('pin_number')

    def get_is_save_user_token(self, data):
        data = self.context.get('request').data
        return data.get('is_save_user_token')

    def get_customer_name(self, data):
        data = self.context.get('request').data
        return data.get('customer_name')

    def get_token(self, data):
        data = self.context.get('request').data
        return data.get('token')

    def get_cvv(self, data):
        data = self.context.get('request').data
        return data.get('cvv')

    def get_session_id(self, data):
        data = self.context.get('request').data
        return data.get('session_id')

    def get_session_data(self, data):
        data = self.context.get('request').data
        return data.get('session_data')

    @property
    def transaction_obj(self):
        data = self.context.get('request').data
        transaction_id = data.get('transaction_id')
        from services.v1.views.common import YouPayTransactionCRUD
        obj = YouPayTransactionCRUD()
        transaction_obj = obj.get_youpay_transaction_data(
            decrypt_string(transaction_id))
        if transaction_obj:
            return transaction_obj
        else:
            raise serializers.ValidationError((
                "QitafOTPSerializer : Transaction not found with ID"
                " {}".format(transaction_id)))

    def get_token_type(self, data):
        data = self.context.get('request').data
        return data.get('token_type')
