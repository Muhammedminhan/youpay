from django.urls import path

from gateways.paypal.webhook_listner import WebhookListner

urlpatterns = [
    path('webhook',WebhookListner.as_view()),
]
