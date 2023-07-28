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
            invoice = str(request_data.get('invoice', None))
            logger.info("B2cpayback webhook received for invoice {} is "
                        "{}".format(invoice, request_data))

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
