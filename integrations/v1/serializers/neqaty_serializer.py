from rest_framework import serializers


class NeqatyRedemptionSerializer(serializers.Serializer):
    selected_amount = serializers.SerializerMethodField()
    checkout_amount = serializers.SerializerMethodField()
    one_time_password = serializers.SerializerMethodField()
    is_save_user_token = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    token = serializers.SerializerMethodField()
    cvv = serializers.SerializerMethodField()
    token_type = serializers.SerializerMethodField()

    def get_selected_amount(self, data):
        data = self.context.get('request').data
        return data.get('selected_amount')

    def get_checkout_amount(self, data):
        data = self.context.get('request').data
        return data.get('checkout_amount')

    def get_one_time_password(self, data):
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

    def get_token_type(self, data):
        data = self.context.get('request').data
        return data.get('token_type')