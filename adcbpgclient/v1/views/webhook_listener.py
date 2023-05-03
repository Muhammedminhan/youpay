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
from integrations.v1.gateway_clients.b2c_payback import B2CPaybackManager
from payments.models import YouPayTransactionData

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


class WebhookListener(APIView):
    authentication_classes = (SignatureAuthentication, )

    def post(self, request):
        request_data = json.loads(request.data)
        try:
            b2cpayback_obj = B2CPaybackManager()
            invoice = str(request_data.get('invoice', None))
            logger.info("B2cpayback webhook received for invoice {}".format(
                invoice))

            reference = request_data.get('reference_id', None)
            purchase_obj = get_purchase_request_object(reference)
            if purchase_obj:
                logger.info(
                    "B2cpayback webhook listener updating data for invoice "
                    "{0}".format(invoice))
                serializer = ADCBTransactionDataSerializer(
                    purchase_obj, data=request_data, partial=True)
            else:
                serializer = ADCBTransactionDataSerializer(
                    data=request_data, partial=True)

            if serializer.is_valid(raise_exception=True):
                serializer.save()
                data_to_update = self.prepare_youpay_transaction_update_data(
                    request_data, reference)
                if data_to_update:
                    b2cpayback_obj.update_youpay_transaction_data(
                        data_to_update)
                    logger.info("B2cpayback webhook listener updated "
                                "youpaytransactiondata for reference "
                                "{}".format(reference))
                response_data = {'message': "B2cpayback webhook listener "
                                            "successfully processed data",
                                 'status': True}
                logger.info("B2cpayback webhook successfully processed data "
                            "for invoice {}".format(invoice))
            else:
                response_data = {'message': "B2cpayback webhook listener "
                                            "data processing failed",
                                 'status': False}
                logger.info(
                    "B2cpayback webhook was unable to process data for "
                    "invoice {} because {}".format(invoice,
                                                   serializer.errors))
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

    def prepare_youpay_transaction_update_data(self, request_data, reference):
        try:
            transaction_obj = (
                self.get_youpay_transaction_data_with_payment_reference(
                    reference))
            if transaction_obj:
                data_to_update = {
                    'transaction_id': transaction_obj.transaction_id,
                    'redeemed_amount': request_data.get("redeemed_amount"),
                    'redeemed_points': request_data.get("redeemed_points"),
                    'payable_amount': request_data.get("payable_amount"),
                    'available_amount': request_data.get("available_amount"),
                    'available_points': request_data.get("available_points"),
                    'is_full_redemption': request_data.get(
                        "is_full_redemption")
                }
                return data_to_update
            else:
                logger.info(
                    "Transaction object not found for payment reference "
                    "{}".format(reference))
                return None
        except Exception as e:
            logger.error("Error while preparing data for youpay transaction "
                         "update {}".format(e))

    def get_youpay_transaction_data_with_payment_reference(self,
                                                           payment_reference):
        try:
            transaction_obj = YouPayTransactionData.objects.get(
                payment_reference=payment_reference)
            return transaction_obj
        except YouPayTransactionData.DoesNotExist:
            logger.error(
                "Unable to find youpay transaction object with payment"
                "_reference {}".format(payment_reference))
            return None
