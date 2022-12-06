import logging

from django.contrib import admin
from django.core.cache import cache

from core.admin import AdminAbstract
from integrations.models import PaymentGateway, PaymentGatewayAPI
from .constants import (B2CP_CACHE_KEY, CHECKOUTPG_CACHE_KEY,
                        AMAZONPG_CACHE_KEY, TABBYPG_CACHE_KEY)

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


admin.site.register(PaymentGateway, PaymentGatewayAdmin)
admin.site.register(PaymentGatewayAPI, PaymentGatewayAPIAdmin)
