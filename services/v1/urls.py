from django.urls import path, include
from rest_framework.routers import DefaultRouter

from services.v1.api_clients.b2c_payback import (B2CPaybackPointBalance,
                                                 B2CPaybackAuthenticate,
                                                 B2CPaybackRedemption,
                                                 B2CPaybackVerify)
from services.v1.api_clients.checkoutpg import (SavedCardPayment, CardPayment,
                                                CheckoutVerification,
                                                PaypalPayment)
from services.v1.views.configurations import ConfigViewSet
from .api_clients.amazonpg import (AmazonPGAuthentication,
                                   AmazonPGVerification, AmazonPGTokenization)
from .api_clients.tabbypg import CreateSession, TabbyPGVerification
from .api_clients.happy_credits import (HappyCreditsCreditBalance,
                                        HappyCreditsDebitBalance)
from .views.client_registration import APIClientRegistrationViewSet
from .views.payment import (PaymentRequestView, TestPaymentRequestView,
                            PaymentCancelledView, TransactionExpireView)

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
    path('checkout/paypal/', PaypalPayment.as_view()),
    path('checkout/verify/', CheckoutVerification.as_view(),
         name='checkout_verify'),
    path('payment-cancel/', PaymentCancelledView.as_view()),
    path('payment-expire/', TransactionExpireView.as_view()),

    # b2cpayback endpoints
    path('adcb/point-balance/', B2CPaybackPointBalance.as_view()),
    path('adcb/authenticate/', B2CPaybackAuthenticate.as_view()),
    path('adcb/redemption/', B2CPaybackRedemption.as_view()),
    path('adcb/verification/', B2CPaybackVerify.as_view()),

    # Tabbypg endpoints
    path('tabbypg/createsession/', CreateSession.as_view()),
    path('tabbypg/verify/', TabbyPGVerification.as_view()),

    # Amazonpg endpoints
    path('amazonpg/tokenization/', AmazonPGTokenization.as_view()),
    path('amazonpg/authentication/', AmazonPGAuthentication.as_view()),
    path('amazonpg/verify/', AmazonPGVerification.as_view()),

    # Happy Credits endpoints
    path('happycredits/credit-balance/', HappyCreditsCreditBalance.as_view()),
    path('happycredits/redemption/', HappyCreditsDebitBalance.as_view()),
]
