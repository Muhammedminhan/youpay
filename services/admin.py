from django.contrib import admin

from core.admin import AdminAbstract
from services.models import APIClient, PaymentRequestData


# Register your models here.

class APICLientAdmin(AdminAbstract):
    list_display = ('name', 'client_domain', 'api_key', 'is_active',
                    'endpoint_url', 'client_code', 'created_at', 'updated_at')
    search_fields = ('name', 'api_key', 'endpoint_url', 'client_domain')
    list_filter = ('created_at', 'is_active')


class PaymentRequestDataAdmin(admin.ModelAdmin):
    list_display = ('api_client', 'amount', 'created_by', 'customer_email', 
                    'created_at', 'updated_at',)
    readonly_fields = ('created_at', 'updated_at', 'created_by',
                       'modified_by', 'customer_email', )
    search_fields = ('api_client__name', 'created_by', 'customer_email')
    list_filter = ('created_at',)


admin.site.register(APIClient, APICLientAdmin)
admin.site.register(PaymentRequestData, PaymentRequestDataAdmin)
