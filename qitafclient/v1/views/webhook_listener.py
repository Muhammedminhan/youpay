import json
import logging

from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from adcbpgclient.libs.authentication import SignatureAuthentication
from qitafclient.models import QitafPayment
from qitafclient.v1.serializers.qitaf_data_serializer import \
    QitafPaymentDataSerializer

logger = logging.getLogger(__name__)


def get_redemption_request_object(reference):
    with transaction.atomic():
        redemption_obj = None
        if reference:
            try:
                redemption_obj = (
                    QitafPayment.objects.select_for_update().get(
                        reference_id=reference))
            except QitafPayment.DoesNotExist:
                redemption_obj = None
        return redemption_obj


class WebhookListener(APIView):
    authentication_classes = (SignatureAuthentication,)

    def post(self, request):
        request_data = json.loads(request.data)
        try:
            reference_id = str(request_data.get('reference_id', None))
            logger.info("b2cp/Qitaf webhook received for reference_id {}, "
                        "data {}".format(reference_id, request_data))

            reference = request_data.get('reference_id', None)
            redemption_obj = get_redemption_request_object(reference)
            if redemption_obj:
                logger.info(
                    "b2cp/Qitaf webhook listener updating data for invoice "
                    "{0}".format(reference_id))
                serializer = QitafPaymentDataSerializer(
                    redemption_obj, data=request_data, partial=True)
            else:
                serializer = QitafPaymentDataSerializer(
                    data=request_data, partial=True)

            if serializer.is_valid(raise_exception=True):
                serializer.save()
                response_data = {'message': "b2cp/Qitaf webhook listener "
                                            "successfully processed data",
                                 'status': True}
                logger.info(
                    "b2cp/Qitaf webhook successfully processed data "
                    "for payment reference {}".format(reference_id))
            else:
                response_data = {'message': "b2cp/Qitaf webhook listener "
                                            "data processing failed",
                                 'status': False}
                logger.info(
                    "b2cp/Qitaf webhook was unable to process data for "
                    "invoice {} because {}".format(reference_id,
                                                   serializer.errors))
            return self.pg_response('HTTP_200_OK', data=response_data)
        except Exception as e:
            logger.error("b2cp/Qitaf webhook processing "
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
