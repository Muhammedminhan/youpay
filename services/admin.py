from django.contrib import admin

from core.admin import AdminAbstract
from services.models import APIClient, PaymentRequestData
from services.forms import APIClientForm


class APIClientAdmin(AdminAbstract):
    form = APIClientForm
    list_display = ('name', 'client_domain', 'api_key', 'is_active',
                    'webhook_url', 'client_code', 'created_at', 'updated_at')
    search_fields = ('name', 'api_key', 'webhook_url', 'client_domain')
    list_filter = ('created_at', 'is_active')


class PaymentRequestDataAdmin(admin.ModelAdmin):
    list_display = ('order_reference', 'api_client', 'amount',
                    'customer_email', 'created_at', 'updated_at',)
    readonly_fields = (
        'created_at', 'updated_at', 'customer_email', 'customer_phone')
    search_fields = (
        'api_client__name', 'customer_email', "invoice_id", "order_reference")
    list_filter = ('created_at', 'api_client', 'currency')
    raw_id_fields = ('api_client',)


admin.site.register(APIClient, APIClientAdmin)
admin.site.register(PaymentRequestData, PaymentRequestDataAdmin)
