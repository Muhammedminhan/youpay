from django.urls import path

from services.v1.views.views import APIClientRegistrationView

urlpatterns = [
    path('registration/client/', APIClientRegistrationView.as_view()),
    path('registration/client/<str:pk>', APIClientRegistrationView.as_view()),
]
