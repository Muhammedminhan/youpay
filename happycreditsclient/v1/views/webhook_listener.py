import decimal
import json
import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from happycreditsclient.models import HappyCreditsClientData
from happycreditsclient.libs.authentication import SignatureAuthentication
from django.db import transaction as db_transaction
from amazonpgclient.utils import wait_redis_lock

logger = logging.getLogger(__name__)


class WebhookListener(APIView):

    authentication_classes = (SignatureAuthentication,)

    def post(self, request):
        request_data = json.loads(request.data)
        try:
            payment_reference = request_data.get('payment_reference', None)
            logger.info("Happy credits webhook received for payment {}"
                        "".format(payment_reference))

            lock_name = 'lock:HappyCreditsWebhookListener:invoice_%d' % (1,)
            with wait_redis_lock(lock_name=lock_name):
                transaction_obj = self.get_transaction_object(
                    payment_reference)
                if transaction_obj:
                    transaction_obj.status = request_data.get(
                        'status')
                    transaction_obj.request_data = json.dumps(request_data)
                    transaction_obj.transaction_id = request_data.get(
                        'transaction_id')
                    transaction_obj.customer_email = request_data.get(
                        'user_email')
                    transaction_obj.save()
                else:
                    transaction_obj = HappyCreditsClientData.objects.create(
                        transaction_id=request_data.get('transaction_id'),
                        request_data=json.dumps(request_data),
                        status=request_data.get('status'),
                        customer_email=request_data.get('user_email'),
                        payment_reference=request_data.get(
                            'payment_reference')
                    )
                response_data = {'message': "HappyCredits webhook listener "
                                            "successfully processed data",
                                 'status': True}
                logger.info("HappyCredits webhook successfully processed "
                            "for payment {}".format(payment_reference))
                return self.pg_response('HTTP_200_OK', data=response_data)
        except Exception as e:
            response_data = {'message': "Data not  updated", 'status': False}
            logger.error("HappyCredits webhook failed with error {}".format(e))
            return self.pg_response('HTTP_500_INTERNAL_SERVER_ERROR',
                                    data=response_data)

    def get_transaction_object(self, payment_reference):
        with db_transaction.atomic():
            transaction = None
            if payment_reference:
                try:
                    transaction = (
                        HappyCreditsClientData.objects.select_for_update(
                        ).get(payment_reference=payment_reference))
                except HappyCreditsClientData.DoesNotExist:
                    transaction = None
            return transaction

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
