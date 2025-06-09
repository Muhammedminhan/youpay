from django.contrib import admin

from core.admin import AdminAbstract
from gateways.paypal.models import PaymentAccessToken, PaypalTransaction


class PaymentAccessTokenAdmin(AdminAbstract):
    list_display = ('access_token', 'created_at')
    readonly_fields = ('access_token', 'created_at')


class PaypalTransactionAdmin(AdminAbstract):
    list_display = (
        'payment_reference', 'order_id', 'currency', 'amount', 'status',
        'created_at')
    search_fields = ('payment_reference', 'order_id', 'currency', 'amount')
    list_filter = ('status', 'currency')


admin.site.register(PaymentAccessToken, PaymentAccessTokenAdmin)
admin.site.register(PaypalTransaction, PaypalTransactionAdmin)
