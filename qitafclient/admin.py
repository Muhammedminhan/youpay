from django.contrib import admin

from .models import QitafPayment


class QitafPaymentDataAdmin(admin.ModelAdmin):
    list_display = (
        'reference_id', 'MSISDN', 'customer_name', 'amount',
        'redemption_status', 'is_reversed', 'is_full_redemption',
        'request_id', 'created_on', 'modified_on')
    search_fields = (
        'reference_id', 'request_id', 'invoice', 'customer_email',)
    list_filter = (
        'is_full_redemption', 'redemption_status', 'platform')


admin.site.register(QitafPayment, QitafPaymentDataAdmin)
