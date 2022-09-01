from rest_framework import serializers

from payments.models import YGPayTransactionData


class YGPayTransactionDataSerializer(serializers.ModelSerializer):
    session_id = serializers.CharField(max_length=255, required=True)

    class Meta:
        model = YGPayTransactionData
        fields = '__all__'
