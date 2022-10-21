from .views import WebhookListener
from django.urls import path

urlpatterns = [
    path('webhook/', WebhookListener.as_view()),
]
