from turtle import mode
from django.db import models

# Create your models here.

PAYMENT_GATEWAY_API_TYPE = [
    ('create', 'Create'),
    ('authorize', 'Authorize'),
    ('verify', 'Verify'),
    ('capture', 'Capture'),
    ('expire', 'Expire'),
    ('cancell', 'Cancell'),
    ('refund', 'Refund'),
    ('callback', 'Callback'),
    ('close', 'Close'),
]

PAYMENT_REQUEST_METHOD = [
    ('post', 'POST'),
    ('get', 'GET'),
]

API_VERSIONS = [
    ('v1', 'v1'),
    ('v2', 'v2'),
    ('v3', 'v3'),
    ('v4', 'v4'),
    ('v5', 'v5'),
    ('v6', 'v6'),
    ('v7', 'v7'),
    ('v8', 'v8'),
    ('v9', 'v9'),
    ('v10', 'v10'),
]


class PaymentGateway(models.Model):
    gateway_name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    domain = models.URLField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.gateway_name


class PaymentGatewayAPI(models.Model):
    api_name = models.CharField(max_length=255)
    payment_gateway = models.ForeignKey(PaymentGateway,
                                        on_delete=models.CASCADE)
    api_path = models.CharField(max_length=255, blank=False, null=False)
    description = models.TextField(null=True, blank=True)
    api_key = models.CharField(max_length=255, blank=True, null=True)
    api_secret = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    request_method = models.CharField(max_length=255,
                                      choices=PAYMENT_REQUEST_METHOD)
    api_type = models.CharField(max_length=255,
                                choices=PAYMENT_GATEWAY_API_TYPE)
    api_version = models.CharField(max_length=255, blank=True, null=True,
                                   choices=API_VERSIONS)

    def __str__(self):
        return self.payment_gateway.gateway_name + self.api_name
