from django.contrib import admin

from .models import PurchaseRequest


class PurchaseRequestAdmin(admin.ModelAdmin):

    list_display = ('reference_id', 'invoice', 'customer_email',
                    'redemption_status', 'currency',
                    'amount', 'created_on', 'modified_on')
    search_fields = ('reference_id', 'invoice', 'customer_name',
                     'customer_email')
    list_filter = ('platform', 'is_full_redemption', 'redemption_status',
                   'payment_status', 'redemption_method')


admin.site.register(PurchaseRequest, PurchaseRequestAdmin)
