from rest_framework import serializers

from amazonpgclient.models import AmazonPGTransactionData


class TransactionDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = AmazonPGTransactionData
        fields = '__all__'
