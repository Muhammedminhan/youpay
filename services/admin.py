from django.contrib import admin

from core.admin import AdminAbstract
from services.forms import APIClientForm
from services.models import (APIClient, PaymentRequestData, ConfigurationData,
                             OfferDetails)
from services.tasks import sync_configuration_data


from modeltranslation.admin import TranslationAdmin


class APIClientAdmin(TranslationAdmin, AdminAbstract):
    form = APIClientForm
    list_display = ('name', 'client_domain', 'api_key', 'is_active',
                    'webhook_url', 'client_code', 'created_at', 'updated_at')
    search_fields = ('name', 'api_key', 'webhook_url', 'client_domain')
    list_filter = ('created_at', 'is_active')


class PaymentRequestDataAdmin(admin.ModelAdmin):
    list_display = ('order_reference', 'api_client', 'amount',
                    'customer_email', 'created_at', 'updated_at',)
    readonly_fields = (
        'created_at', 'updated_at', 'customer_email', 'customer_phone',
        'customer_uid')
    search_fields = (
        'api_client__name', 'customer_email', "invoice_id", "order_reference")
    list_filter = ('created_at', 'api_client', 'currency')
    raw_id_fields = ('api_client',)


class ConfigurationDataAdmin(admin.ModelAdmin):
    list_display = ('payment_gateway', 'currency', 'created_at', 'updated_at',)
    readonly_fields = ('created_at', 'updated_at')
    search_fields = ('payment_gateway__gateway_name', 'currency')
    list_filter = ('created_at', 'payment_gateway', 'currency')
    raw_id_fields = ('payment_gateway',)

    actions = ['sync_conf_data']

    def sync_conf_data(self, request, queryset):
        """
        It will update latest configuration data
        """
        for item in queryset:
            sync_configuration_data.delay(item.payment_gateway.code,
                                          item.currency.iso_code)

    sync_conf_data.short_description = "Sync Configuration Data"


class OfferDetailsAdmin(admin.ModelAdmin):
    list_display = ("invoice_id", "client", "created_at", "updated_at")
    search_fields = ("invoice_id",)
    list_filter = ("client", "created_at")
    readonly_fields = ("created_at", "updated_at")


admin.site.register(APIClient, APIClientAdmin)
admin.site.register(PaymentRequestData, PaymentRequestDataAdmin)
admin.site.register(ConfigurationData, ConfigurationDataAdmin)
admin.site.register(OfferDetails, OfferDetailsAdmin)
