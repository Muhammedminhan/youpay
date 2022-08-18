from django.contrib import admin

from core.admin import AdminAbstract
from integrations.models import PaymentGateway, PaymentGatewayAPI


# Register your models here.
class PaymentGatewayAdmin(AdminAbstract):
    list_display = (
        'gateway_name', 'is_active', 'domain', 'api_key', 'api_secret',
        'created_at', 'updated_at')
    search_fields = ('gateway_name', 'domain', 'api_key', 'api_secret')
    list_filter = ('is_active', 'created_at')


class PaymentGatewayAPIAdmin(AdminAbstract):
    list_display = (
        'api_name', 'api', 'payment_gateway', 'api_path', 'created_at',
        'updated_at')
    search_fields = ('api_name', 'payment_gateway__gateway_name', 'api_path')
    list_filter = ('request_method', 'api_type', 'created_at')

    def api(self, obj):
        return " ({}) ".format(
            obj.api_type) + obj.payment_gateway.domain + obj.api_path


admin.site.register(PaymentGateway, PaymentGatewayAdmin)
admin.site.register(PaymentGatewayAPI, PaymentGatewayAPIAdmin)
