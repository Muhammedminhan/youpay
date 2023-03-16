from django.urls import path

from amazonpgclient.v1.views.amazonpg_webhook_listener import WebhookListener

urlpatterns = [
    path('webhook/', WebhookListener.as_view(),
         name='payment'),
]
