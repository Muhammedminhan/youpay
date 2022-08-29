from django.urls import path

from checkoutpgclient.v1.views.webhook_listener import WebhookListener

urlpatterns = [
    path('webhook/', WebhookListener.as_view(),
         name='payment'),
]
