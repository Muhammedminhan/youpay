from django.contrib import admin

from core.admin import AdminAbstract
from integrations.models import YoupayToPaymentGatewaysData
from payments.models import (YouPayTransactionData, Announcement,
                             ClientNotification)


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
        'customer_phone', 'loyalty_level')
    search_fields = ('transaction_id', 'customer_email', 'invoice_id',
                     'payment_reference', 'order_reference')
    list_filter = ('created_at', 'payment_status', 'api_client',
                   'payment_gateway', 'currency', "platform")
    raw_id_fields = ('api_client',)

    inlines = [
        YoupayToPaymentGatewaysDataInline,
    ]


class AnnouncementAdmin(AdminAbstract):
    list_display = ('gateway', 'offer_message', 'is_active',
                    'created_at', 'updated_at')
    search_fields = ('gateway__gateway_name', 'offer_message')
    list_filter = ('created_at', 'gateway__gateway_name', 'is_active')
    raw_id_fields = ('gateway',)


class ClientNotificationAdmin(admin.ModelAdmin):
    list_display = ('transaction', 'api_client', 'is_notified', 'event_type',
                    'payment_status','created_at', 'updated_at',)
    search_fields = ('transaction__transaction_id', 'api_client__name',)
    list_filter = ('created_at', 'api_client__name', 'is_notified',
                   'payment_status',)
    raw_id_fields = ('transaction', 'api_client',)
    readonly_fields = ('created_at', 'updated_at')

admin.site.register(YouPayTransactionData, YouPayTransactionDataAdmin)
admin.site.register(Announcement, AnnouncementAdmin)
admin.site.register(ClientNotification, ClientNotificationAdmin)
