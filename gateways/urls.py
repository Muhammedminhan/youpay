from django.urls import path

from gateways.paypal.webhook_listner import WebhookListner
from gateways.tpay.webhook_listner import TPayWebhookListener

urlpatterns = [
    path('webhook',WebhookListner.as_view()),
    path('tpay/webhook', TPayWebhookListener.as_view()),
]
