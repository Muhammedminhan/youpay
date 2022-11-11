"""youpay URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, re_path
from django.conf.urls import include
from core.views import HealthCheck
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.contrib.staticfiles.views import serve


def trigger_error(request):
    division_by_zero = 1 / 0


urlpatterns = [
    path('alonzo-mckinney/admin/control-panel/', admin.site.urls),
    path('services/', include('services.urls')),
    path('health/', HealthCheck.as_view(), name='health'),
    path('sentry-debug/', trigger_error),
    path('checkoutpg/', include('checkoutpgclient.urls')),
    path('amazontpg/', include('amazonpgclient.urls')),
]

urlpatterns += staticfiles_urlpatterns()
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    # static files (images, css, javascript, etc.)
    urlpatterns += [re_path(r'^media/(?P<path>.*)$', serve)]
    urlpatterns += [re_path(r'^static/(?P<path>.*)$', serve)]
