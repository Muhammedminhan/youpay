import json
import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from tabbypgclient.libs.authentication import SignatureAuthentication
from tabbypgclient.models import TabbyPaymentData
from tabbypgclient.utils import wait_redis_lock

logger = logging.getLogger(__name__)
from django.db import transaction


class TabbyWebhookListener(APIView):
    authentication_classes = (SignatureAuthentication,)

    def post(self, request):
        print("INFO : Webhook request is {}".format(request.data))
        response_data = {}
        logger.info("webhook triggered {}".format(request))
        request_data = json.loads(request.data)
        try:
            logger.info("Tabbypg webhook received for {}".format(
                request_data.get("payment_reference")))

            lock_name = 'lock:WebhookListener:invoice_%d' % (1,)
            with wait_redis_lock(lock_name=lock_name):

                transaction_obj = self.get_tabby_payment_object(
                    request_data.get(
                        'payment_reference', None))
                if transaction_obj:
                    transaction_obj.amount = request_data.get('amount')
                    transaction_obj.currency = request_data.get('currency')
                    transaction_obj.customer_name = request_data.get(
                        'customer_name')
                    transaction_obj.customer_email = request_data.get(
                        'customer_email')
                    transaction_obj.customer_ip_address = request_data.get('')
                    transaction_obj.payment_id = request_data.get(
                        'payment_id')
                    transaction_obj.status = request_data.get('status')
                    transaction_obj.request_source = request_data.get('')
                    transaction_obj.platform = request_data.get('platform')
                    transaction_obj.is_paid = request_data.get('is_paid')
                    transaction_obj.invoice_id = request_data.get(
                        'invoice_id', None)
                    transaction_obj.save()

                else:
                    transaction_obj = TabbyPaymentData.objects.create(
                        order_reference=request_data.get('order_reference'),
                        amount=request_data.get('amount'),
                        currency=request_data.get('currency'),
                        customer_name=request_data.get('customer_name'),
                        customer_email=request_data.get('customer_email'),
                        customer_ip_address=request_data.get(''),
                        payment_id=request_data.get('payment_id'),
                        status=request_data.get('status'),
                        request_source=request_data.get(''),
                        payment_reference=request_data.get(
                            'payment_reference'),
                        platform=request_data.get('platform'),
                        is_paid=request_data.get('is_paid'),
                        invoice_id=request_data.get('invoice_id', None)
                    )
                    transaction_obj.save()
                response_data = {'status': True}
                return self.pg_response('HTTP_200_OK', data=response_data)
        except Exception as e:
            logger.error("Tabbypg webhook failed with error {}".format(e))
            response_data = {'message': "Data not  updated", 'status': False}
            return self.pg_response('HTTP_500_INTERNAL_SERVER_ERROR',
                                    data=response_data)

    def get_tabby_payment_object(self, payment_reference):
        transaction_data = None
        if payment_reference:
            try:
                with transaction.atomic():
                    transaction_data = (
                        TabbyPaymentData.objects.select_for_update().get(
                            payment_reference=payment_reference))
            except TabbyPaymentData.DoesNotExist:
                transaction_data = None
        return transaction_data

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
