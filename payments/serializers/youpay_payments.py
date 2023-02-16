from rest_framework import serializers

from payments.models import YouPayTransactionData


class YouPayTransactionDataSerializer(serializers.ModelSerializer):
    session_id = serializers.CharField(max_length=255, required=True)

    class Meta:
        model = YouPayTransactionData
        fields = '__all__'
