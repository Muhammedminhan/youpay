from django.urls import path, include

urlpatterns = [
    path('api/v1/', include('networkpg.v1.urls')),
]
