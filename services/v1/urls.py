from django.urls import path

from .views.client_registration import APIClientRegistrationView
from .views.payment import PaymentRequestView

urlpatterns = [
    # TODO - restructure the api paths
    path('registration/client/', APIClientRegistrationView.as_view()),
    path('registration/client/<str:pk>', APIClientRegistrationView.as_view()),
    path('create/transaction/', PaymentRequestView.as_view()),
    # TODO
    #  - Create config api - merge with checkoutpg config api
    #  - create delete stored card api
    #  - get stored card api - card payment api
    #  - get ADCB point balance API
    #  - ADCB authentication api
    #  - ADCB redemption api

]
