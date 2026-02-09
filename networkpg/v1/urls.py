from django.urls import path
from .views.payment import NetworkPaymentsApi
from .views.webhook import NetworkWebhookListener

urlpatterns = [
    path('payments/', NetworkPaymentsApi.as_view(), name='network-payments'),
    path('webhook/', NetworkWebhookListener.as_view(), name='network-webhook'),
]
