from django.urls import include
from django.urls import path

from .v1.views.webhook_listener import WebhookListener

urlpatterns = [
    path('api/v1/', include('adcbpgclient.v1.urls')),
]
