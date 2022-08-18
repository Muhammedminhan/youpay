from django.contrib import admin

from core.admin import AdminAbstract
from services.models import APIClient

# Register your models here.

class APICLientAdmin(AdminAbstract):
    list_display = ('name', 'client_domain', 'api_key', 'is_active', 
                    'endpoint_url','client_code', 'created_at')
    search_fields = ('name', 'api_key', 'endpoint_url','client_domain')
    list_filter = ('created_at', 'is_active')

admin.site.register(APIClient, APICLientAdmin)
