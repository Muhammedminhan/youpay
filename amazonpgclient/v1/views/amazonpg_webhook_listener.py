import decimal
import json
import logging

from django.db import transaction as db_transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from amazonpgclient.libs.authentication import SignatureAuthentication
from amazonpgclient.models import AmazonPGTransactionData
from amazonpgclient.utils import wait_redis_lock

logger = logging.getLogger(__name__)


class WebhookListener(APIView):

    authentication_classes = (SignatureAuthentication,)

    def post(self, request):

        request_data = json.loads(request.data)
        try:

            payment_reference = request_data.get('payment_reference', None)
            logger.info("Amazonpg webhook received for payment {}".format(
                payment_reference))

            lock_name = ('lock:AmazonPGWebhookListener:'
                         'payment_reference_%s' % (payment_reference,))
            with wait_redis_lock(lock_name=lock_name):
                transaction_obj = self.get_transaction_object(
                    payment_reference)
                if transaction_obj:
                    transaction_obj.payment_status = request_data.get(
                        'payment_status')
                    transaction_obj.apg_payment_status = request_data.get(
                        'apg_payment_status')
                    transaction_obj.authorization_code = request_data.get(
                        'authorization_code', None)
                    transaction_obj.response_code = request_data.get(
                        'response_code', None)
                    transaction_obj.response_message = request_data.get(
                        'response_message', None)
                    transaction_obj.acquirer_response_code = request_data.get(
                        'acquirer_response_code', None)
                    transaction_obj.fort_id = request_data.get('fort_id',
                                                               None)
                    transaction_obj.is_fraud = request_data.get(
                        'is_fraud')
                    transaction_obj.is_flagged = request_data.get(
                        'is_flagged')

                    transaction_obj.save()
                else:
                    transaction_obj = AmazonPGTransactionData.objects.create(
                        customer_email=request_data.get('customer_email'),
                        customer_phone=request_data.get('customer_phone'),
                        customer_name=request_data.get('customer_name'),
                        transaction_id=request_data.get('transaction_id'),
                        amount=decimal.Decimal(request_data.get('amount')),
                        currency=request_data.get('currency'),
                        invoice_id=request_data.get('invoice_id'),
                        order_reference=request_data.get('order_reference'),
                        payment_reference=request_data.get(
                            'payment_reference'),
                        is_fraud=request_data.get('is_fraud'),
                        is_flagged=request_data.get('is_flagged'),
                        fort_id=request_data.get('fort_id'),
                        payment_status=request_data.get('payment_status'),
                        apg_payment_status=request_data.get(
                            'apg_payment_status'),
                        card_bin=request_data.get('card_bin'),
                        card_last4=request_data.get('card_last4'),
                        authorization_code=request_data.get(
                            'authorization_code'),
                        response_code=request_data.get('response_code'),
                        response_message=request_data.get('response_message'),
                        acquirer_response_code=request_data.get(
                            'acquirer_response_code')
                    )
                response_data = {'message': "AmazonPG webhook listener "
                                            "successfully processed data",
                                 'status': True}
                logger.info("Amazonpg webhook successfully processed "
                            "for payment {}".format(payment_reference))
                return self.pg_response('HTTP_200_OK', data=response_data)
        except Exception as e:
            response_data = {'message': "Data not  updated", 'status': False}
            logger.error("Amazonpg webhook failed with error {}".format(e))
            return self.pg_response('HTTP_500_INTERNAL_SERVER_ERROR',
                                    data=response_data)

    def get_transaction_object(self, payment_reference):
        with db_transaction.atomic():
            transaction = None
            if payment_reference:
                try:
                    transaction = (
                        AmazonPGTransactionData.objects.select_for_update(
                        ).get(payment_reference=payment_reference))
                except AmazonPGTransactionData.DoesNotExist:
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
