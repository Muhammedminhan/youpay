import json
import logging

from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from citirewardsclient.models import CitiRedemptionData
from adcbpgclient.libs.authentication import SignatureAuthentication
from citirewardsclient.v1.serializers.citi_redemption_data_serializer import (
    CitiRedemptionDataSerializer)

logger = logging.getLogger(__name__)


def get_redemption_request_object(reference):
    with transaction.atomic():
        redemption_obj = None
        if reference:
            try:
                redemption_obj = (
                    CitiRedemptionData.objects.select_for_update().get(
                       reference_id=reference))
            except CitiRedemptionData.DoesNotExist:
                redemption_obj = None
        return redemption_obj


class WebhookListener(APIView):
    authentication_classes = (SignatureAuthentication, )

    def post(self, request):
        request_data = json.loads(request.data)
        try:
            invoice = str(request_data.get('invoice', None))
            logger.info("B2cpayback webhook received for invoice {}".format(
                invoice))

            reference = request_data.get('reference_id', None)
            redemption_obj = get_redemption_request_object(reference)
            if redemption_obj:
                logger.info(
                    "B2cpayback webhook listener updating data for invoice "
                    "{0}".format(invoice))
                serializer = CitiRedemptionDataSerializer(
                    redemption_obj, data=request_data, partial=True)
            else:
                serializer = CitiRedemptionDataSerializer(
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
