from rest_framework import serializers


class HassadPaymentRequestSerializer(serializers.Serializer):
    invoice_id = serializers.SerializerMethodField()
    platform = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    customer_email = serializers.SerializerMethodField()
    language_code = serializers.SerializerMethodField()
    mobile_number = serializers.SerializerMethodField()
    reference_id = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()
    currency = serializers.SerializerMethodField()
    is_full_redemption = serializers.SerializerMethodField()
    amount_in_aed = serializers.SerializerMethodField()
    ip = serializers.SerializerMethodField()

    def get_invoice_id(self, data):
        return data.get('transaction_obj').invoice_id

    def get_platform(self, data):
        return data.get('transaction_obj').platform

    def get_customer_name(self, data):
        return data.get('transaction_obj').customer_name

    def get_customer_email(self, data):
        return data.get('transaction_obj').customer_email

    def get_language_code(self, data):
        return data.get('transaction_obj').language

    def get_mobile_number(self, data):
        return data.get('transaction_obj').customer_phone

    def get_reference_id(self, data):
        return data.get('transaction_obj').payment_reference

    def get_amount(self, data):
        return str(data.get('transaction_obj').base_amount)

    def get_currency(self, data):
        return data.get('transaction_obj').currency

    def get_is_full_redemption(self, data):
        return data.get('transaction_obj').is_full_redemption

    def get_amount_in_aed(self, data):
        return str(data.get('transaction_obj').amount_in_aed)

    def get_ip(self, data):
        return data.get('transaction_obj').ip
