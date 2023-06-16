from django.urls import path

from .views.webhook_listener import WebhookListener


urlpatterns = [
    path('webhook/', WebhookListener.as_view(), name='citi_rewards_webhook'),
    ]
