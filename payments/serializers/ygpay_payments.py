from rest_framework import serializers

from payments.models import YOUPayTransactionData


class YOUPayTransactionDataSerializer(serializers.ModelSerializer):
    session_id = serializers.CharField(max_length=255, required=True)

    class Meta:
        model = YOUPayTransactionData
        fields = '__all__'
