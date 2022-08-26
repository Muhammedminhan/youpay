from django.urls import path

from services.v1.views.views import (APIClientRegistrationView,
                                     PaymentRequestView)

urlpatterns = [
    path('registration/client/', APIClientRegistrationView.as_view()),
    path('registration/client/<str:pk>', APIClientRegistrationView.as_view()),
    path('create/transaction/', PaymentRequestView.as_view()),
]
