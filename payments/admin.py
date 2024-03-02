from django.contrib import admin

from core.admin import AdminAbstract
from integrations.models import YoupayToPaymentGatewaysData
from payments.adminActions import archive_transaction_data
from payments.forms import AnnouncementForm
from payments.models import (YouPayTransactionData, Announcement,
                             ClientNotification, AdditionalCharge,
                             ArchivedYouPayTransactionData)


class YoupayToPaymentGatewaysDataInline(admin.TabularInline):
    readonly_fields = ('created_at', 'updated_at',)
    model = YoupayToPaymentGatewaysData
    extra = 0
    can_delete = False


class YouPayTransactionDataAdmin(admin.ModelAdmin):
    actions = [archive_transaction_data]
    archive_transaction_data.short_description = (
        "Archive Selected Transaction data")

    list_display = ('transaction_id', 'amount', 'currency', 'customer_email',
                    'payment_status', 'invoice_id', 'order_reference',
                    'payment_reference', 'api_client',
                    'payment_Gateway', 'created_at', 'updated_at',)
    readonly_fields = (
        'transaction_id', 'created_at', 'updated_at', 'customer_email',
        'customer_phone', 'loyalty_level')
    search_fields = ('transaction_id', 'customer_email', 'invoice_id',
                     'payment_reference', 'order_reference')
    list_filter = ('settlement_entity', 'payment_status', 'api_client',
                   'payment_gateway', 'payment_method', 'currency',
                   "platform", "is_gcc_card", "is_flagged", "is_fraud",
                   'created_at', 'is_guest')
    raw_id_fields = ('api_client',)

    inlines = [
        YoupayToPaymentGatewaysDataInline,
    ]

    fieldsets = (
        ('Customer details', {
            'fields': ('customer_name', 'customer_email', 'customer_phone',
                       'is_guest', 'ip', 'language',
                       )
        }),
        ('Card details', {
            'fields': ('name_on_card', 'card_bin', 'card_last4',
                       'card_issuer_country', 'is_gcc_card',
                       )
        }),
        ('Order details', {
            'fields': ('invoice_id', 'order_reference', 'api_client',
                       'order_history', 'payment_status', 'approved',
                       'order_items',
                       )
        }),
        ('Cart details', {
            'fields': ('cart_amount', 'cart_currency', 'cart_service_fee',
                       'cart_base_amount', 'cart_VAT_amount', 'brand_details',
                       'brand_calculations'
                       )
        }),
        ('Payment details', {
            'fields': ('amount', 'amount_in_aed', 'currency', 'country_code',
                       'transaction_id', 'payment_reference',
                       'settlement_entity', 'payment_gateway',
                       'channel_code', 'payment_method', 'payment_scheme',
                       'platform', 'response_summary', 'service_fee',
                       'base_amount', 'VAT_amount', 'gateway_charge',
                       'is_payment_verified'
                       )
        }),
        ('URLs', {
            'fields': ('success_url', 'failure_url', 'cancel_url',
                       'verify_url',
                       )
        }),
        ('Risk details', {
            'fields': ('is_fraud', 'is_flagged',
                       )
        }),
        ('B2C Payback transaction details', {
            'fields': ('redeemed_amount', 'redeemed_points', 'payable_amount',
                       'available_amount', 'available_points',
                       'is_full_redemption', 'earned_point',
                       'points_collected_mobile_number',
                       'points_redeemed_mobile_number',
                       'points_collection_enabled_program',
                       'point_collection_enabled',
                       'maximum_redeemable_points',
                       'minimum_redeemable_points', 'amount_conversion_rate',
                       'citi_order_id', 'citi_phone_number'
                       )
        }),
        ('Happycredits transaction details', {
            'fields': ('credit_balance_amount', 'available_credit_balance',
                       )
        }),
        ('Paypal Additional Fee details', {
            'fields': ('additional_currency_decimal_notation',
                       'additional_vat_percentage', 'additional_vat',
                       'additional_processing_fee',
                       'additional_processing_fee_vat',
                       'additional_total_amount',
                       )
        }),
        ('Quitaf transaction details', {
            'fields': ('qitaf_phone_number', 'is_qitaf_enabled',
                       )
        }),
        ('Other Details', {
            'fields': ('retry_count', 'session_id', 'loyalty_level',
                       'created_at', 'updated_at'
                       )
        }),
    )

    def payment_Gateway(self, obj):
        if obj.payment_gateway:
            display_string = f"{obj.payment_gateway}"
            if obj.payment_method:
                display_string = f"{display_string} ({obj.payment_method})"

            return display_string
        else:
            return None


class AnnouncementAdmin(AdminAbstract):
    form = AnnouncementForm
    list_display = (
        'gateway', 'payment_option', 'offer_message', 'platform', 'is_active',
        'created_at', 'updated_at')
    search_fields = ('gateway__gateway_name', 'offer_message', 'platform')
    list_filter = ('created_at', 'gateway__gateway_name', 'is_active',
                   'platform')
    raw_id_fields = ('gateway',)


class ClientNotificationAdmin(admin.ModelAdmin):
    list_display = (
        'get_transaction', 'api_client', 'is_notified', 'event_type',
        'payment_status', 'created_at', 'updated_at',)
    search_fields = ('transaction__transaction_id', 'api_client__name',)
    list_filter = ('created_at', 'api_client__name', 'is_notified',
                   'payment_status',)
    raw_id_fields = ('transaction', 'api_client',)
    readonly_fields = ('created_at', 'updated_at')

    def get_transaction(self, obj):
        return obj.transaction.transaction_id

    get_transaction.admin_order_field = 'transaction'
    get_transaction.short_description = 'youpay transaction id'


class AdditionalChargeAdmin(admin.ModelAdmin):
    list_display = (
        'get_transaction', 'payment_option', 'additional_vat',
        'additional_processing_fee', 'additional_total_amount',
        'created_at', 'updated_at',)
    search_fields = ('transaction__transaction_id', 'payment_option')
    list_filter = ('created_at',)
    raw_id_fields = ('transaction',)
    readonly_fields = ('payment_option', 'created_at', 'updated_at')

    def get_transaction(self, obj):
        return obj.transaction.transaction_id

    get_transaction.admin_order_field = 'transaction'
    get_transaction.short_description = 'youpay transaction id'


class ArchivedYouPayTransactionDataAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'amount', 'currency', 'customer_email',
                    'payment_status', 'invoice_id', 'order_reference',
                    'payment_reference', 'created_at', 'api_client',
                    'payment_gateway', 'updated_at', 'archived_at')
    readonly_fields = (
        'transaction_id', 'created_at', 'updated_at', 'customer_email',
        'customer_phone', 'loyalty_level', 'archived_at')
    search_fields = ('transaction_id', 'customer_email', 'invoice_id',
                     'payment_reference', 'order_reference')
    list_filter = ('settlement_entity', 'payment_status', 'api_client',
                   'payment_gateway', 'payment_method', 'currency',
                   "platform", "is_gcc_card", "is_flagged", "is_fraud",
                   'created_at', 'is_guest')
    raw_id_fields = ('api_client',)

    fieldsets = (
        ('Customer details', {
            'fields': ('customer_name', 'customer_email', 'customer_phone',
                       'is_guest', 'ip', 'language',
                       )
        }),
        ('Card details', {
            'fields': ('name_on_card', 'card_bin', 'card_last4',
                       'card_issuer_country', 'is_gcc_card',
                       )
        }),
        ('Order details', {
            'fields': ('invoice_id', 'order_reference', 'api_client',
                       'order_history', 'payment_status', 'approved',
                       'order_items',
                       )
        }),
        ('Cart details', {
            'fields': ('cart_amount', 'cart_currency', 'cart_service_fee',
                       'cart_base_amount', 'cart_VAT_amount', 'brand_details',
                       'brand_calculations'
                       )
        }),
        ('Payment details', {
            'fields': ('amount', 'amount_in_aed', 'currency', 'country_code',
                       'transaction_id', 'payment_reference',
                       'settlement_entity', 'payment_gateway',
                       'channel_code', 'payment_method', 'payment_scheme',
                       'platform', 'response_summary', 'service_fee',
                       'base_amount', 'VAT_amount', 'gateway_charge',
                       'is_payment_verified'
                       )
        }),
        ('URLs', {
            'fields': ('success_url', 'failure_url', 'cancel_url',
                       'verify_url',
                       )
        }),
        ('Risk details', {
            'fields': ('is_fraud', 'is_flagged',
                       )
        }),
        ('B2C Payback transaction details', {
            'fields': ('redeemed_amount', 'redeemed_points', 'payable_amount',
                       'available_amount', 'available_points',
                       'is_full_redemption', 'earned_point',
                       'points_collected_mobile_number',
                       'points_redeemed_mobile_number',
                       'points_collection_enabled_program',
                       'point_collection_enabled',
                       )
        }),
        ('CITI transaction details', {
            'fields': ('maximum_redeemable_points',
                       'minimum_redeemable_points', 'amount_conversion_rate',
                       'citi_order_id', 'citi_phone_number'
                       )
        }),
        ('Happycredits transaction details', {
            'fields': ('credit_balance_amount', 'available_credit_balance',
                       )
        }),
        ('Paypal Additional Fee details', {
            'fields': ('additional_currency_decimal_notation',
                       'additional_vat_percentage', 'additional_vat',
                       'additional_processing_fee',
                       'additional_processing_fee_vat',
                       'additional_total_amount',
                       )
        }),
        ('Other Details', {
            'fields': ('retry_count', 'session_id', 'loyalty_level',
                       'created_at', 'updated_at',
                       'archived_at'
                       )
        }),
    )


admin.site.register(YouPayTransactionData, YouPayTransactionDataAdmin)
admin.site.register(ArchivedYouPayTransactionData,
                    ArchivedYouPayTransactionDataAdmin)
admin.site.register(Announcement, AnnouncementAdmin)
admin.site.register(ClientNotification, ClientNotificationAdmin)
admin.site.register(AdditionalCharge, AdditionalChargeAdmin)
