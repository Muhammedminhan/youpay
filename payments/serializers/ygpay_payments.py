from rest_framework import serializers

from payments.models import YGPayTransactionData


class YGPayTransactionDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = YGPayTransactionData
        fields = '__all__'
