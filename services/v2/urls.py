from django.urls import path

from services.v2.api_clients.checkoutpg import (SavedCardPayment,
                                                CreatePaymentSession,
                                                SubmitPaymentSession)

urlpatterns = [
    path('checkout/saved-card/', SavedCardPayment.as_view(),
         name='SavedCardPayment'),
    path('checkout/sessions/', CreatePaymentSession.as_view(),
         name='CreatePaymentSession'),
    path('checkout/sessions/submit/', SubmitPaymentSession.as_view(),
         name='SubmitPaymentSession'),
]
