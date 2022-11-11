from django.contrib import admin, messages

from .models import TabbyPaymentData


class TabbyPaymentDataAdmin(admin.ModelAdmin):
    model = TabbyPaymentData

    list_display = (
        'payment_reference', 'customer_email', 'is_paid', 'amount',
        'payment_id','invoice_id', 'status', 'created_on',
        'modified_on')
    actions = ('deleted_selected_items',)
    search_fields = ('payment_reference', 'customer_email',"invoice_id")
    list_filter = ("created_on", "currency", "status", "platform", "is_paid")

    def deleted_selected_items(self, request, queryset):
        queryset.delete()

    deleted_selected_items.short_description = (
        'Delete selected items')


admin.site.register(TabbyPaymentData, TabbyPaymentDataAdmin)
