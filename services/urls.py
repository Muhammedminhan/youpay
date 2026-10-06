from django.urls import include
from django.urls import path

urlpatterns = [
    path('api/v1/', include('services.v1.urls')),
    path('api/v2/', include('services.v2.urls')),
    path('api/v3/', include('services.v3.urls')),
]
