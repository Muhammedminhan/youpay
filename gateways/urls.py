from django.urls import include, path

urlpatterns = [
    path('paypal/', include('gateways.paypal.url')),
    path('tpay/', include('gateways.tpay.url')),
]
