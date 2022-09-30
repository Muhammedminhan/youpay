from django.urls import path, include
from rest_framework.routers import DefaultRouter

from services.v1.api_clients.checkoutpg import (SavedCardPayment, CardPayment,
                                                CheckoutVerification)
from services.v1.views.configurations import ConfigViewSet
from .views.client_registration import APIClientRegistrationViewSet
from .views.payment import (PaymentRequestView, TestPaymentRequestView,
                            PaymentCancelledView)

router = DefaultRouter()
router.register('client', APIClientRegistrationViewSet, basename='client')
router.register('youpay_configuration', ConfigViewSet, basename='conf')

urlpatterns = [
    path("", include(router.urls)),
    path('payment/', PaymentRequestView.as_view()),
    # For testing purpose
    # input will be the request data, output will be encrypted data and this
    # will be the input for the payment API
    path('test-payment/', TestPaymentRequestView.as_view()),

    path('checkout/saved-card/', SavedCardPayment.as_view()),
    path('checkout/card/', CardPayment.as_view()),
    path('checkout/verify/', CheckoutVerification.as_view(),
         name='checkout_verify'),
    path('payment-cancel/', PaymentCancelledView.as_view()),

    # TODO
    #  - create delete stored card api
    #  - get stored card api - card payment api
    #  - get ADCB point balance API
    #  - ADCB authentication api
    #  - ADCB redemption api

]
