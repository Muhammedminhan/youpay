from rest_framework import serializers

from b2cpaybackclient.models import PurchaseRequest


class PurchaseRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseRequest
        fields = '__all__'
