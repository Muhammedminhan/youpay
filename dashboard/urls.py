from django.urls import path

from dashboard.views import DashboardView, MonitoringView, FailuresView

app_name = 'dashboard'

urlpatterns = [
    path('', DashboardView.as_view(), name='index'),
    path('monitoring/', MonitoringView.as_view(), name='monitoring'),
    path('failures/', FailuresView.as_view(), name='failures'),
]
