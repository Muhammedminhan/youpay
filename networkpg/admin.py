from django.contrib import admin
from .models import NetworkTransaction, EventNotification


@admin.register(NetworkTransaction)
class NetworkTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'payment_reference',
        'order_reference',
        'amount',
        'currency',
        'status',
        'is_approved',
        'created_on'
    )
    list_filter = ('status', 'is_approved', 'currency', 'created_on')
    search_fields = (
        'payment_reference',
        'order_reference',
        'network_order_id',
        'network_order_reference',
        'customer_email',
        'customer_name'
    )
    readonly_fields = ('created_on', 'modified_on',)
    ordering = ('-created_on',)
    raw_id_fields = ('youpay_transaction',)


@admin.register(EventNotification)
class EventNotificationAdmin(admin.ModelAdmin):
    list_display = (
        'event_type',
        'payment_reference',
        'processed',
        'processed_at',
        'created_on'
    )
    list_filter = ('processed', 'event_type', 'created_on')
    search_fields = ('payment_reference', 'event_type')
    readonly_fields = ('created_on', 'processed_at', 'raw_data')
    ordering = ('-created_on',)
    raw_id_fields = ('network_transaction',)
