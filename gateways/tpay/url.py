from django.urls import path

from gateways.tpay.webhook_listner import TPayWebhookListener

urlpatterns = [
    path('webhook', TPayWebhookListener.as_view()),
]
