from rest_framework import serializers

from qitafclient.models import QitafPayment


class QitafPaymentDataSerializer(serializers.ModelSerializer):

    class Meta:
        model = QitafPayment
        fields = '__all__'
