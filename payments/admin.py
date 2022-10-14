from django.contrib import admin

from integrations.models import YoupayToPaymentGatewaysData
from payments.models import YouPayTransactionData, Announcement


class YoupayToPaymentGatewaysDataInline(admin.TabularInline):
    readonly_fields = ('created_at', 'updated_at',)
    model = YoupayToPaymentGatewaysData
    extra = 0
    can_delete = False


class YouPayTransactionDataAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'amount', 'currency', 'customer_email',
                    'payment_status', 'invoice_id', 'order_reference',
                    'payment_reference', 'created_at', 'api_client',
                    'payment_gateway', 'updated_at',)
    readonly_fields = (
        'transaction_id', 'created_at', 'updated_at', 'customer_email',
        'customer_phone')
    search_fields = ('transaction_id', 'customer_email', 'invoice_id',
                     'payment_reference', 'order_reference')
    list_filter = ('created_at', 'payment_status', 'api_client',
                   'payment_gateway', 'currency', "platform")
    raw_id_fields = ('api_client',)

    inlines = [
        YoupayToPaymentGatewaysDataInline,
    ]


class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('gateway', 'message', 'is_active',
                    'created_at', 'updated_at')
    search_fields = ('gateway__gateway_name', 'message')
    list_filter = ('created_at', 'gateway__gateway_name', 'is_active')
    raw_id_fields = ('gateway',)

admin.site.register(YouPayTransactionData, YouPayTransactionDataAdmin)
admin.site.register(Announcement, AnnouncementAdmin)
