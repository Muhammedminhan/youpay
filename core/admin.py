import logging

from django.contrib import admin

from .models import AppConfig
from django.core.cache import cache

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


admin.site.register(AppConfig, AppConfigAdmin)
