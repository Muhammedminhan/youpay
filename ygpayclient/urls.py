from django.urls import path, include

urlpatterns = [
    path('api/v1/', include('ygpayclient.v1.urls')),
]
