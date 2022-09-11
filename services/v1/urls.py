from django.urls import path, include
from rest_framework.routers import DefaultRouter

from services.v1.views.configurations import ConfigViewSet
from .views.client_registration import APIClientRegistrationViewSet
from .views.payment import PaymentRequestView
from services.v1.api_clients.checkoutpg import SavedCardPayment, CardPayment

router = DefaultRouter()
router.register('client', APIClientRegistrationViewSet, basename='client')
router.register('youpay_configuration', ConfigViewSet, basename='conf')

urlpatterns = [
    path("", include(router.urls)),
    path('payment/', PaymentRequestView.as_view()),
    path('checkout/saved-card/', SavedCardPayment.as_view()),
    path('checkout/card/', CardPayment.as_view()),

    # TODO
    #  - create delete stored card api
    #  - get stored card api - card payment api
    #  - get ADCB point balance API
    #  - ADCB authentication api
    #  - ADCB redemption api

]
