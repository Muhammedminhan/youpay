from rest_framework import serializers


class QitafPaymentRequestSerializer(serializers.Serializer):
    invoice = serializers.SerializerMethodField()
    # reference_id = serializers.SerializerMethodField()
    platform = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    request_id = serializers.SerializerMethodField()
    # request_date = serializers.SerializerMethodField()
    MSISDN = serializers.SerializerMethodField()
    # branch_id = serializers.SerializerMethodField()
    # terminal_id = serializers.SerializerMethodField()
    # ref_request_id = serializers.SerializerMethodField()
    language_code = serializers.SerializerMethodField()
    mobile_number = serializers.SerializerMethodField()

    def get_invoice(self, data):
        print("\n\nDATA ", data)
        print("\n\nDATA ", data.get('transaction_obj'))
        print("\n\nDATA ", data.get('transaction_obj').invoice_id)
        return data.get('transaction_obj').invoice_id

    # def get_reference_id(self, data):
    #     return data.get('transaction_obj').reference_id

    def get_platform(self, data):
        return data.get('transaction_obj').platform

    def get_customer_name(self, data):
        return data.get('transaction_obj').customer_name

    def get_request_id(self, data):
        return data.get('transaction_obj').qitaf_request_id

    # def get_request_date(self, data):
    #     return data.get('transaction_obj').created_at

    def get_MSISDN(self, data):
        return data.get('transaction_obj').qitaf_phone_number

    def get_language_code(self, data):
        return "en-us"

    def get_mobile_number(self, data):
        return data.get('transaction_obj').customer_phone
