from django.contrib import admin

from .models import CitiRedemptionData


class CitiRedemptionDataAdmin(admin.ModelAdmin):

    list_display = ('reference_id', 'request_id', 'customer_email',
                    'redemption_status', 'currency',
                    'amount', 'created_on', 'modified_on')
    search_fields = ('reference_id', 'request_id', 'customer_name',
                     'customer_email', 'invoice')
    list_filter = ('platform', 'is_full_redemption', 'redemption_status',
                   'redemption_method')


admin.site.register(CitiRedemptionData, CitiRedemptionDataAdmin)
