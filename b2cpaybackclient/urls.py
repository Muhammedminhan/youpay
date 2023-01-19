from django.urls import path

from .v1.views.webhook_listener import WebhookListener

urlpatterns = [
    path('webhook/', WebhookListener.as_view(),
         name='b2cpayback_payment'),
]
