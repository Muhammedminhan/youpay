from django.http import HttpResponse
from django.views.generic import View


class HealthCheck(View):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        request.session.delete(request.session.session_key)
        request.session.modified = False
        return HttpResponse(status=200)
