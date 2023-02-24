from django.contrib import admin

from .models import HappyCreditsClientData

# Register your models here.


class HappyCreditsClientDataAdmin(admin.ModelAdmin):
    model = HappyCreditsClientData

    list_display = ('transaction_id', 'payment_reference', 'status',
                    'customer_email', 'created_at', 'updated_at')
    search_fields = ('transaction_id', 'payment_reference', 'customer_email')
    list_filter = ('status', )


admin.site.register(HappyCreditsClientData, HappyCreditsClientDataAdmin)
