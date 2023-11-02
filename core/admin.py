import logging

from django.contrib import admin
from django.core.cache import cache

from .models import AppConfig, Currency, Country, PaymentMethod

admin.site.site_header = 'YouPay Administration'

logger = logging.getLogger(__name__)


class AdminAbstract(admin.ModelAdmin):
    readonly_fields = (
        'created_at', 'updated_at', 'created_by', 'modified_by')
    exclude = ('created_by', 'modified_by', 'created_at', 'updated_at')

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        if form.changed_data:
            obj.modified_by = request.user
        super().save_model(request, obj, form, change)


class AppConfigAdmin(admin.ModelAdmin):
    list_display = ('front_end_domain', 'created_at', 'updated_at')
    readonly_fields = (
        'created_at', 'updated_at', 'created_by', 'modified_by')
    exclude = ('created_by', 'modified_by', 'created_at', 'updated_at')

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        if form.changed_data:
            try:
                cache.delete('app_config')
            except (TypeError, AttributeError):
                logging.error(
                    'Error while clearing bulk order config cache')

            obj.modified_by = request.user
        super().save_model(request, obj, form, change)


class CurrencyAdmin(AdminAbstract):
    list_display = ('iso_code', 'name', 'decimal_notation',
                    'created_at', 'updated_at')
    search_fields = ('iso_code', 'name',)
    list_filter = ('created_by', )


class CountryAdmin(AdminAbstract):
    list_display = ('name', 'iso_code', 'flag', 'currency',
                    'is_gcc', 'created_at')
    search_fields = ('name', 'iso_code', 'currency')
    list_filter = ('currency', 'is_gcc', 'three_letter_code',)
    raw_id_fields = ('currency',)


class PaymentMethodAdmin(AdminAbstract):
    fields = ('payment_method', 'country', 'clients', 'active',
              'guest_user_enabled', 'payment_gateway', 'created_at',
              'updated_at', 'created_by', 'modified_by')
    list_display = ('payment_method', 'active',
                    'guest_user_enabled', 'payment_gateway')
    search_fields = ('payment_method', 'country', 'clients')
    list_filter = ('payment_method', 'active', 'guest_user_enabled',
                   'payment_gateway',)
    filter_horizontal = ('clients', 'country')

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return ('created_at', 'updated_at', 'created_by', 'modified_by')
        return (
            'payment_method', 'payment_gateway', 'created_at', 'updated_at',
            'created_by', 'modified_by')


admin.site.register(AppConfig, AppConfigAdmin)
admin.site.register(Currency, CurrencyAdmin)
admin.site.register(Country, CountryAdmin)
admin.site.register(PaymentMethod, PaymentMethodAdmin)
