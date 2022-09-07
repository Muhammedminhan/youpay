from django.urls import path
from django.conf.urls import include

urlpatterns = [
    path('api/v1/', include('services.v1.urls')),
]
