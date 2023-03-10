from rest_framework import serializers

from happycreditsclient.models import HappyCreditsClientData


class HappyCreditsDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = HappyCreditsClientData
        fields = '__all__'
