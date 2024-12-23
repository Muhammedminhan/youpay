from django.contrib import admin

from notifications.models import EmailTemplateConfiguration


# Register your models here.

class EmailTemplateConfigurationAdmin(admin.ModelAdmin):
    list_display = ('email_type', 'template_code', 'is_active')
    search_fields = ('email_type', 'template_code')
    list_filter = ('is_active', 'email_type')


admin.site.register(EmailTemplateConfiguration, EmailTemplateConfigurationAdmin)