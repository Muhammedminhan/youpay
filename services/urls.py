from django.urls import path, include

urlpatterns = [
    path('api/v1/', include('services.v1.urls')),
]
