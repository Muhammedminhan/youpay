from rest_framework import serializers

from core.validators import URLValidator
from integrations.models import PaymentGateway
from services.models import APIClient
from payments.models import Announcement

class APIClientRegistrationSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=255, required=True)
    webhook_url = serializers.CharField(max_length=255, required=True,
                                        validators=[URLValidator()])
    client_domain = serializers.CharField(max_length=255, required=True,
                                          validators=[URLValidator()])

    class Meta:
        model = APIClient
        fields = '__all__'


class APIClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = APIClient
        fields = '__all__'


class PaymentGatewaySerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentGateway
        fields = '__all__'


class AnnouncementSerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        data = super(AnnouncementSerializer, self).to_representation(
            instance)
        return data['message']

    class Meta:
        model = Announcement
        fields = ('message',)


class PaymentGatewayAnnouncementSerializer(serializers.ModelSerializer):
    gateway_announcement = AnnouncementSerializer(many=True, read_only=True)

    def to_representation(self, instance):
        data = super(PaymentGatewayAnnouncementSerializer,
                     self).to_representation(instance)
        return data['gateway_name'], data['gateway_announcement']

    class Meta:
        model = PaymentGateway
        fields = ('gateway_name','gateway_announcement')
