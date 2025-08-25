import logging

from django.contrib import admin
from django.core.cache import cache

from core.admin import AdminAbstract
from integrations.models import (
    PaymentGateway, PaymentGatewayAPI, PaymentOptions,
    AdditionalChargeConfiguration, GatewayChargeConfiguration,
    YoupayToPaymentGatewaysData)
from integrations.forms import (AdditionalChargeConfigurationAdminForm,
                                GatewayChargeConfigurationAdminForm)
from .constants import (B2CP_CACHE_KEY, CHECKOUTPG_CACHE_KEY,
                        AMAZONPG_CACHE_KEY, TABBYPG_CACHE_KEY,
                        HAPPYCREDITS_CACHE_KEY)

logger = logging.getLogger(__name__)


class PaymentGatewayAdmin(AdminAbstract):
    list_display = (
        'gateway_name', 'is_active', 'domain', 'api_key', 'api_secret',
        'created_at', 'updated_at')
    search_fields = ('gateway_name', 'domain', 'api_key', 'api_secret')
    list_filter = ('is_active', 'created_at')

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        if form.changed_data:
            try:
                cache.delete(CHECKOUTPG_CACHE_KEY)
                cache.delete(B2CP_CACHE_KEY)
                cache.delete(AMAZONPG_CACHE_KEY)
                cache.delete(TABBYPG_CACHE_KEY)
                cache.delete(HAPPYCREDITS_CACHE_KEY)
            except (TypeError, AttributeError):
                logging.error(
                    'Error while clearing bulk gateway config cache')
            obj.modified_by = request.user
        super().save_model(request, obj, form, change)


class PaymentGatewayAPIAdmin(AdminAbstract):
    list_display = (
        'api_name', 'api', 'payment_gateway', 'api_path', 'created_at',
        'updated_at')
    search_fields = ('api_name', 'payment_gateway__gateway_name', 'api_path')
    list_filter = ('request_method', 'api_type', 'created_at')

    def api(self, obj):
        return " ({}) ".format(
            obj.api_type) + obj.payment_gateway.domain + obj.api_path


class PaymentOptionsAdmin(AdminAbstract):
    list_display = ('name', 'gateway',)
    search_fields = ('name', 'gateway__gateway_name',)
    list_filter = ('gateway', 'created_by',)


class AdditionalChargeConfigurationAdmin(AdminAbstract):
    form = AdditionalChargeConfigurationAdminForm
    list_display = ('payment_option', 'charge_type', 'currency', 'percentage',
                    'VAT_percentage', 'is_active', 'created_at', 'updated_at')
    search_fields = ('payment_option__name',)
    list_filter = ('payment_option', 'created_by',)


class GatewayChargeConfigurationAdmin(AdminAbstract):
    form = GatewayChargeConfigurationAdminForm
    list_display = ('payment_mode', 'charge_type', 'fixed_amount',
                    'percentage', 'currency', 'is_active', 'created_at',
                    'updated_at')
    search_fields = ('payment_mode__name',)
    list_filter = ('payment_mode', 'created_by',)


class YoupayToPaymentGatewaysDataAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'request_type', 'request_method',
                    'created_at', 'updated_at')
    search_fields = ('youpay_payment__transaction_id',)
    list_filter = ('request_type', 'created_at')

    def transaction_id(self, obj):
        return obj.youpay_payment.transaction_id


admin.site.register(PaymentGateway, PaymentGatewayAdmin)
admin.site.register(PaymentGatewayAPI, PaymentGatewayAPIAdmin)
admin.site.register(PaymentOptions, PaymentOptionsAdmin)
admin.site.register(AdditionalChargeConfiguration,
                    AdditionalChargeConfigurationAdmin)
admin.site.register(GatewayChargeConfiguration,
                    GatewayChargeConfigurationAdmin)
admin.site.register(YoupayToPaymentGatewaysData,
                    YoupayToPaymentGatewaysDataAdmin)
