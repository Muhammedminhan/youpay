from rest_framework import serializers

from citirewardsclient.models import CitiRedemptionData


class CitiRedemptionDataSerializer(serializers.ModelSerializer):

    class Meta:
        model = CitiRedemptionData
        fields = '__all__'
