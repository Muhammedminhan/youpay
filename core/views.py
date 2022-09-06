from django.shortcuts import render
from django.views.generic import View
from django.http import Http404, HttpResponse


class HealthCheck(View):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        request.session.delete(request.session.session_key)
        request.session.modified = False
        return HttpResponse(status=200)
