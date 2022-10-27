from rest_framework import serializers


class TabbyPGPaymentRequestSerializer(serializers.Serializer):
    currency = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()
    order_reference = serializers.SerializerMethodField()
    invoice_id = serializers.SerializerMethodField()
    payment_reference = serializers.SerializerMethodField()

    loyality_level = serializers.SerializerMethodField()
    registered_since = serializers.SerializerMethodField()
    language = serializers.SerializerMethodField()
    platform = serializers.SerializerMethodField()

    order_items = serializers.SerializerMethodField()
    order_history = serializers.SerializerMethodField()

    customer_email = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    customer_ip_address = serializers.SerializerMethodField()
    customer_phone = serializers.SerializerMethodField()

    cancel_url = serializers.SerializerMethodField()
    failure_url = serializers.SerializerMethodField()
    success_url = serializers.SerializerMethodField()

    def get_currency(self, data):
        return data.get('transaction_data').get("currency")

    def get_amount(self, data):
        return str(data.get('transaction_data').get("amount"))

    def get_order_reference(self, data):
        return data.get('transaction_data').get("order_reference")

    def get_invoice_id(self, data):
        return data.get('transaction_data').get("invoice_id")

    def get_payment_reference(self, data):
        return data.get('transaction_data').get("payment_reference")

    def get_loyality_level(self, data):
        return data.get("loyality_level")

    def get_registered_since(self, data):
        return data.get('transaction_data').get("registered_since")

    def get_language(self, data):
        return data.get("language")

    def get_platform(self, data):
        return data.get('transaction_data').get("platform")

    def get_order_items(self, data):
        return data.get('transaction_data').get("order_items")

    def get_order_history(self, data):
        return data.get('transaction_data').get("order_history")

    def get_customer_email(self, data):
        return data.get('transaction_data').get("customer_email")

    def get_customer_name(self, data):
        return data.get('transaction_data').get("customer_name")

    def get_customer_ip_address(self, data):
        return data.get('transaction_data').get("ip")

    def get_customer_phone(self, data):
        return data.get('transaction_data').get("customer_phone")

    def get_cancel_url(self, data):
        return data.get('transaction_data').get("cancel_url")

    def get_failure_url(self, data):
        return data.get('transaction_data').get("failure_url")

    def get_success_url(self, data):
        return data.get('transaction_data').get("success_url")
