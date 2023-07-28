import json
import logging

from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from adcbpgclient.models import ADCBTransactionData
from adcbpgclient.libs.authentication import SignatureAuthentication
from adcbpgclient.v1.serializers.adcbtransactiondata_serializer import (
    ADCBTransactionDataSerializer)
from integrations.common import WebhookDataFormat

logger = logging.getLogger(__name__)


def get_purchase_request_object(reference):
    with transaction.atomic():
        purchase_obj = None
        if reference:
            try:
                purchase_obj = (
                    ADCBTransactionData.objects.select_for_update().get(
                       reference_id=reference))
            except ADCBTransactionData.DoesNotExist:
                purchase_obj = None
        return purchase_obj


class WebhookListener(APIView, WebhookDataFormat):
    authentication_classes = (SignatureAuthentication,)

    def post(self, request):
        request_data = json.loads(request.data)
        try:
            invoice = str(request_data.get('invoice', None))
            logger.info("B2cpayback webhook received for invoice {} is "
                        "{}".format(invoice, request_data))

            reference = request_data.get('reference_id', None)
            transaction_obj = get_purchase_request_object(reference)
            if transaction_obj:
                logger.info(
                    "B2cpayback webhook listener updating data for invoice "
                    "{0}".format(invoice))
                transaction_obj.request_id = request_data.get(
                    'request_id')
                transaction_obj.invoice = request_data.get('invoice')
                transaction_obj.reference_id = request_data.get(
                    'reference_id')
                transaction_obj.card_number = request_data.get(
                    'card_number')
                transaction_obj.card_expiry = request_data.get(
                    'card_expiry')
                transaction_obj.encrypted_card_number = request_data.get(
                    'encrypted_card_number')
                transaction_obj.encrypted_card_expiry = request_data.get(
                    'encrypted_card_expiry')
                transaction_obj.platform = request_data.get(
                    'platform')
                transaction_obj.customer_name = request_data.get(
                    'customer_name')
                transaction_obj.amount = request_data.get(
                    'amount')
                transaction_obj.currency = request_data.get(
                    'currency')
                transaction_obj.amount_in_aed = request_data.get(
                    'amount_in_aed')
                transaction_obj.redemption_amount = request_data.get(
                    'redemption_amount')
                transaction_obj.redeemed_amount = request_data.get(
                    'redeemed_amount')
                transaction_obj.redeemed_points = request_data.get(
                    'redeemed_points')
                transaction_obj.payable_amount = request_data.get(
                    'payable_amount')
                transaction_obj.available_amount = request_data.get(
                    'available_amount')
                transaction_obj.available_points = request_data.get(
                    'available_points')
                transaction_obj.is_full_redemption = request_data.get(
                    'is_full_redemption')
                transaction_obj.redemption_status = request_data.get(
                    'redemption_status')
                transaction_obj.payment_status = request_data.get(
                    'payment_status')
                transaction_obj.redemption_method = request_data.get(
                    'redemption_method')
                transaction_obj.customer_email = request_data.get(
                    'customer_email')
                transaction_obj.auth_code = request_data.get(
                    'auth_code')
                transaction_obj.is_fraud = request_data.get(
                    'is_fraud')
                transaction_obj.is_flagged = request_data.get(
                    'is_flagged')
                transaction_obj.card_issuer_country = request_data.get(
                    'card_issuer_country')
                transaction_obj.payment_id = request_data.get(
                    'payment_id')
                transaction_obj.financial_action_response_data = (
                    request_data.get(
                        'financial_action_response_data'))
                if request_data.get('checkoutpg_response_data'):
                    transaction_obj.issuer_bank = self.get_issuer_bank(
                        request_data.get('checkoutpg_response_data'))
                    transaction_obj.three_ds_check = self.get_three_ds(
                        request_data.get('checkoutpg_response_data'))
                    transaction_obj.cvv_check = self.get_cvv_check(
                        request_data.get('checkoutpg_response_data'))
                transaction_obj.save()
            else:
                transaction_obj = ADCBTransactionData.objects.create(
                    request_id=request_data.get(
                        'request_id'),
                    invoice=request_data.get('invoice'),
                    reference_id=request_data.get(
                        'reference_id'),
                    card_number=request_data.get(
                        'card_number'),
                    card_expiry=request_data.get(
                        'card_expiry'),
                    encrypted_card_number=request_data.get(
                        'encrypted_card_number'),
                    encrypted_card_expiry=request_data.get(
                        'encrypted_card_expiry'),
                    platform=request_data.get(
                        'platform'),
                    customer_name=request_data.get(
                        'customer_name'),
                    amount=request_data.get(
                        'amount'),
                    currency=request_data.get(
                        'currency'),
                    amount_in_aed=request_data.get(
                        'amount_in_aed'),
                    redemption_amount=request_data.get(
                        'redemption_amount'),
                    redeemed_amount=request_data.get(
                        'redeemed_amount'),
                    redeemed_points=request_data.get(
                        'redeemed_points'),
                    payable_amount=request_data.get(
                        'payable_amount'),
                    available_amount=request_data.get(
                        'available_amount'),
                    available_points=request_data.get(
                        'available_points'),
                    is_full_redemption=request_data.get(
                        'is_full_redemption'),
                    redemption_status=request_data.get(
                        'redemption_status'),
                    payment_status=request_data.get(
                        'payment_status'),
                    redemption_method=request_data.get(
                        'redemption_method'),
                    customer_email=request_data.get(
                        'customer_email'),
                    auth_code=request_data.get(
                        'auth_code'),
                    is_fraud=request_data.get(
                        'is_fraud'),
                    is_flagged=request_data.get(
                        'is_flagged'),
                    card_issuer_country=request_data.get(
                        'card_issuer_country'),
                    payment_id=request_data.get(
                        'payment_id'),
                    financial_action_response_data=(
                        request_data.get(
                            'financial_action_response_data')),
                )
            response_data = {'message': "B2cpayback webhook listener "
                                        "successfully processed data",
                             'status': True}
            logger.info("B2cpayback webhook successfully processed data "
                        "for invoice {}".format(invoice))
            return self.pg_response('HTTP_200_OK', data=response_data)
        except Exception as e:
            logger.error("B2cpayback webhook processing "
                         "failed with error {}".format(e), exc_info=e)
            response_data = {'message': "Data not  updated", 'status': False}
            return self.pg_response('HTTP_500_INTERNAL_SERVER_ERROR',
                                    data=response_data)

    def pg_response(self, code='HTTP_200_OK', data=None):
        return Response(
            headers={'status': getattr(status, code)},
            status=getattr(status, code),
            data={
                'status': getattr(status, code),
                'data': data
            },
            content_type='application/json'
        )
