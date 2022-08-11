from django.urls import path, include

urlpatterns = [
    path('api/v1/', include('core.v1.urls')),
]
