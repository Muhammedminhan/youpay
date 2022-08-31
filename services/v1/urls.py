from django.urls import path, include
from rest_framework.routers import DefaultRouter

from services.v1.views.configurations import ConfigViewSet
from .views.client_registration import APIClientRegistrationViewSet
from .views.payment import PaymentRequestView

router = DefaultRouter()
router.register('client', APIClientRegistrationViewSet, basename='client')
router.register('conf', ConfigViewSet, basename='conf')

urlpatterns = [
    path("", include(router.urls)),
    path('transaction/', PaymentRequestView.as_view()),

    # TODO
    #  - create delete stored card api
    #  - get stored card api - card payment api
    #  - get ADCB point balance API
    #  - ADCB authentication api
    #  - ADCB redemption api

]
