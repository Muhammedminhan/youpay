from django.urls import path, include

urlpatterns = [
    path('api/v1/', include('integrations.v1.urls')),
]
