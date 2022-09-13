from .views import WebhookListener
from django.urls import path

urlpatterns = [
    path('webhooks/', WebhookListener.as_view()),
]
