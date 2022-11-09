from django.urls import path

from .views import TabbyPGWebhookListener

urlpatterns = [
    path('webhook/', TabbyPGWebhookListener.as_view()),
]
