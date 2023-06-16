from rest_framework import serializers

from citirewardsclient.models import CitiRedemptionData


class CitiRedemptionDataSerializer(serializers.ModelSerializer):
    # amount = serializers.DecimalField(
    #     max_digits=12, decimal_places=2, allow_null=True)
    # amount_in_aed = serializers.DecimalField(
    #     max_digits=12, decimal_places=2, allow_null=True)
    # redeemed_amount = serializers.DecimalField(
    #     max_digits=12, decimal_places=2, allow_null=True)
    # redeemed_points = serializers.DecimalField(
    #     max_digits=12, decimal_places=2, allow_null=True)
    # payable_amount = serializers.DecimalField(
    #     max_digits=12, decimal_places=2, allow_null=True)
    # available_amount = serializers.DecimalField(
    #     max_digits=12, decimal_places=2, allow_null=True)
    # available_points = serializers.DecimalField(
    #     max_digits=12, decimal_places=2, allow_null=True)
    # redemption_amount = serializers.DecimalField(
    #     max_digits=12, decimal_places=2, allow_null=True)

    class Meta:
        model = CitiRedemptionData
        fields = '__all__'
