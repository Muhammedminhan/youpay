from django.http import HttpResponse
from django.views.generic import View


class HealthCheck(View):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        return HttpResponse(status=200)
