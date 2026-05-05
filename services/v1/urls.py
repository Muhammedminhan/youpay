from django.urls import path, include
from rest_framework.routers import DefaultRouter

from integrations.v1.gateway_clients.tabbypg import TabbyPaymentCancel
from services.v1.api_clients.b2c_payback import (B2CPaybackPointBalance,
                                                 B2CPaybackAuthenticate,
                                                 B2CPaybackRedemption,
                                                 B2CPaybackVerify,
                                                 CollectProgramManagement,
                                                 CalculateBalance,
                                                 OfferDetails)
from services.v1.api_clients.checkoutpg import (SavedCardPayment, CardPayment,
                                                CheckoutVerification,
                                                PaypalPayment,
                                                ApplePayStatusUpdateAPI)
from services.v1.views.configurations import (ConfigViewSet,
                                              ClientStaticFilesAPI,
                                              RedemptionPartnerPrograms,
                                              UpdateAmounts)
from .api_clients.amazonpg import (AmazonPGAuthentication,
                                   AmazonPGVerification, AmazonPGTokenization,
                                   AmazonPGSavedCard)
from .api_clients.anb_service import (AnbGenerateOTPAPIView,
                                      AnbRedeemPointsAPIView, AnbVerify)
from .api_clients.citi_service import (CitiPointBalanceAPIView,
                                       CitiPointRedemptionAPIView,
                                       CitiGenerateOTPAPIView)
from .api_clients.happy_credits import (HappyCreditsCreditBalance,
                                        HappyCreditsDebitBalance)
from .api_clients.mokafa_service import (UpdateMokafaPhoneNumber,
                                         MokafaaGenerateOTPAPIView,
                                         MokafaaRedeemPointsAPIView,
                                         MokafaaVerify)
from .api_clients.neqaty_service import (NeqatyPointBalanceAPIView,
                                         NeqatyGenerateOTPAPIView,
                                         NeqatyRedeemPointsAPIView,
                                         NeqatyVerify,
                                         UpdateNeqatyPhoneNumber,
                                         NeqatyTransactionSync)
from .api_clients.paypalpg import (PayPalChargeAPIView,
                                   PayPalPaymentAPIView, PayPalVerifyAPIView)
from .api_clients.qitaf_service import (
    QitafGenerateOTPAPIView, QitafRedeemPointsAPIView,
    QitafCollectPointsAPIView, UpdateQitafPhoneNumber, QitafVerify)
from .api_clients.tabbypg import CreateSession, TabbyPGVerification
from .views.client_registration import (APIClientRegistrationViewSet,
                                        APIClientRegistrationView)
from .views.payment import (PaymentRequestView, TestPaymentRequestView,
                            PaymentCancelledView, TransactionExpireView,
                            AdditionalChargeCalculation,
                            EarnRedemptionPartnerPoints)

router = DefaultRouter()
router.register('client', APIClientRegistrationViewSet, basename='client')
router.register('youpay_configuration', ConfigViewSet, basename='conf')

urlpatterns = [
    path("", include(router.urls)),
    path('registration/client/', APIClientRegistrationView.as_view()),
    path('additional-charges/', AdditionalChargeCalculation.as_view()),
    path('payment/', PaymentRequestView.as_view(), name='PaymentRequestView'),
    # For testing purpose
    # input will be the request data, output will be encrypted data and this
    # will be the input for the payment API
    path('test-payment/', TestPaymentRequestView.as_view()),

    path('checkout/saved-card/', SavedCardPayment.as_view(),
         name='SavedCardPayment'),
    path('checkout/card/', CardPayment.as_view(),
         name='CardPayment'),
    path('checkout/paypal/', PaypalPayment.as_view(),
         name='PaypalPayment'),
    path('checkout/verify/', CheckoutVerification.as_view(),
         name='CheckoutVerification'),
    path('payment-cancel/', PaymentCancelledView.as_view()),
    path('payment-expire/', TransactionExpireView.as_view()),
    path('earn-points/', EarnRedemptionPartnerPoints.as_view(),
         name="earn-points"),

    # b2cpayback endpoints
    path('adcb/point-balance/', B2CPaybackPointBalance.as_view()),
    path('adcb/authenticate/', B2CPaybackAuthenticate.as_view(),
         name='B2CPaybackAuthenticate'),
    path('adcb/redemption/', B2CPaybackRedemption.as_view()),
    path('adcb/verification/', B2CPaybackVerify.as_view(),
         name='B2CPaybackVerify'),
    path('b2cpayback/collect-program/<str:pk>',
         CollectProgramManagement.as_view(),
         name='collect_program_management'),
    path('point-program/calculate-balance/', CalculateBalance.as_view()),
    path('b2cpayback/offer-details/<str:pk>', OfferDetails.as_view()),

    # Tabbypg endpoints
    path('tabbypg/createsession/', CreateSession.as_view(),
         name='TabbyPGCreateSession'),
    path('tabbypg/verify/', TabbyPGVerification.as_view(),
         name='TabbyPGVerification'),
    path('tabbypg/back-to-store/', TabbyPaymentCancel.as_view()),

    # Amazonpg endpoints
    path('amazonpg/tokenization/', AmazonPGTokenization.as_view()),
    path('amazonpg/authentication/', AmazonPGAuthentication.as_view(),
         name='AmazonPGAuthentication'),
    path('amazonpg/verify/', AmazonPGVerification.as_view(),
         name='AmazonPGVerification'),
    path('amazonpg/saved-card/', AmazonPGSavedCard.as_view(),
         name='AmazonPGSavedCard'),

    # Happy Credits endpoints
    path('happycredits/credit-balance/', HappyCreditsCreditBalance.as_view()),
    path('happycredits/redemption/', HappyCreditsDebitBalance.as_view(),
         name='HappyCreditsDebitBalance'),

    # ApplePay endpoints
    path('applepay/status-update/', ApplePayStatusUpdateAPI.as_view()),

    # API for getting the client logo and color code
    path('client-static-details/', ClientStaticFilesAPI.as_view()),

    # API for getting redemption partner programs list
    path('redemption-partner-programs/', RedemptionPartnerPrograms.as_view()),

    # Citi Rewards endpoints
    path('citi/generate-otp/', CitiGenerateOTPAPIView.as_view(),
         name='CitiGenerateOTPAPIView'),
    path('citi/point-balance/', CitiPointBalanceAPIView.as_view()),
    path('citi/point-redemption/', CitiPointRedemptionAPIView.as_view()),

    # Qitaf endpoints
    path('qitaf/update-phone-number/', UpdateQitafPhoneNumber.as_view()),
    path('qitaf/generate-otp/', QitafGenerateOTPAPIView.as_view()),
    path('qitaf/collect/', QitafCollectPointsAPIView.as_view()),
    path('qitaf/redeem-points/', QitafRedeemPointsAPIView.as_view(),
         name='QitafRedeemPointsAPIView'),
    path('qitaf/verify/', QitafVerify.as_view(), name='QitafVerify'),

    # Neqaty Endpoints
    path('neqaty/point-balance/', NeqatyPointBalanceAPIView.as_view(),
         name='NeqatyPointBalanceAPIView'),
    path('neqaty/generate-otp/', NeqatyGenerateOTPAPIView.as_view(),
         name='NeqatyGenerateOTPAPIView'),
    path('neqaty/redeem-points/', NeqatyRedeemPointsAPIView.as_view()),
    path('neqaty/verify/', NeqatyVerify.as_view(), name='NeqatyVerify'),
    path('neqaty/update-phone-number/', UpdateNeqatyPhoneNumber.as_view()),
    path('neqaty/sync-data/', NeqatyTransactionSync.as_view()),

    # Mokafaa Endpoints
    path('mokafa/update-phone-number/', UpdateMokafaPhoneNumber.as_view()),
    path('mokafaa/generate-otp/', MokafaaGenerateOTPAPIView.as_view(),
         name='MokafaaGenerateOTPAPIView'),
    path('mokafaa/redeem-points/', MokafaaRedeemPointsAPIView.as_view(),
         name='MokafaaRedeemPointsAPIView'),
    path('mokafaa/verify/', MokafaaVerify.as_view(), name='MokafaaVerify'),

    # AnB endpoints
    path('anb/generate-otp/', AnbGenerateOTPAPIView.as_view(),
         name='AnbGenerateOTPAPIView'),
    path('anb/redeem-points/', AnbRedeemPointsAPIView.as_view(),
         name='AnbRedeemPointsAPIView'),
    path('anb/verify/', AnbVerify.as_view(), name='AnbVerify'),

    # API for updating service fee and VAT for a new payment attempt
    path('update-amounts/', UpdateAmounts.as_view()),

    # PayPal Endpoints
    path('paypal/charge/', PayPalChargeAPIView.as_view(), name='PayPalCharge'),
    path('paypal/payment/', PayPalPaymentAPIView.as_view(),
         name='PayPalPayment'),
    path('paypal/verify/', PayPalVerifyAPIView.as_view(), name='PayPalVerify'),
]
