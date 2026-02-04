from django.urls import path

from services.v3.api_clients.checkoutpg import (SavedCardPayment,)

urlpatterns = [
    path('checkout/saved-card/', SavedCardPayment.as_view(),
         name='SavedCardPayment'),

]
