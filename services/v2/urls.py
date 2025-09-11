from django.urls import path

from services.v2.api_clients.checkoutpg import (SavedCardPayment,
                                                CreatePaymentSession)

urlpatterns = [
    path('checkout/saved-card/', SavedCardPayment.as_view(),
         name='SavedCardPayment'),
    path('checkout/create-session/', CreatePaymentSession.as_view(),
         name='CreatePaymentSession'),
]
