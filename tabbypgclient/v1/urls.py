from .views import TabbyWebhookListener
from django.urls import path

urlpatterns = [
    path('webhook/', TabbyWebhookListener.as_view()),
]
