import logging
import json

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from ygpayclient.utils import wait_redis_lock
from ygpayclient.models import YGPayClientTransactionData

logger = logging.getLogger(__name__)


class WebhookListener(APIView):
    """
    This class is to process the webhook data from YGPay
    """

    def post(self, request):
        """
        Post method to receive the data from YGPay
        """
        request_data = json.loads(request.data)
        try:
            logger.info("Received YouPay webhook for invoice {}".format(
                request_data.get("invoice_id")))
            lock_name = 'lock:WebhookListener:invoice_%d' % (
                int(request_data.get("invoice_id")),)
            with wait_redis_lock(lock_name=lock_name):
                transaction_obj = self.get_transaction_data_object(
                    request_data.get(
                        'transaction_id', None))
                if transaction_obj:
                    transaction_obj.payment_reference = request_data.get(
                        'payment_reference')
                    transaction_obj.order_reference = request_data.get(
                        'order_reference')
                    transaction_obj.invoice_id = request_data.get(
                        'invoice_id')
                    transaction_obj.amount = request_data.get(
                        'amount')
                    transaction_obj.currency = request_data.get(
                        'currency')
                    transaction_obj.service_fee = request_data.get(
                        'service_fee')
                    transaction_obj.base_amount = request_data.get(
                        'base_amount')
                    transaction_obj.vat_amount = request_data.get(
                        'VAT_amount')
                    transaction_obj.customer_ip_address = request_data.get(
                        'ip')
                    transaction_obj.customer_email = request_data.get(
                        'customer_email')
                    transaction_obj.payment_gateway = request_data.get(
                        'payment_gateway')
                    transaction_obj.payment_status = request_data.get(
                        'payment_status')
                    transaction_obj.save()

                else:
                    transaction_obj = \
                        YGPayClientTransactionData.objects.create(
                            transaction_id=request_data.get(
                                'transaction_id'),
                            payment_reference=request_data.get(
                                'payment_reference'),
                            order_reference=request_data.get(
                                'order_reference'),
                            invoice_id=request_data.get(
                                'invoice_id'),
                            amount=request_data.get(
                                'amount'),
                            currency=request_data.get(
                                'currency'),
                            service_fee=request_data.get(
                                'service_fee'),
                            base_amount=request_data.get(
                                'base_amount'),
                            vat_amount=request_data.get(
                                'VAT_amount'),
                            customer_ip_address=request_data.get(
                                'ip'),
                            customer_email=request_data.get(
                                'customer_email'),
                            payment_gateway=request_data.get(
                                'payment_gateway'),
                            payment_status=request_data.get(
                                'payment_status')
                        )
                    transaction_obj.save()
                response_data = {'message': "ygpayclient webhook listener "
                                            "successfully processed data",
                                 'status': True}
                response_status = status.HTTP_200_OK
        except Exception as e:
            logger.error("ygpayclient webhook failed with error {}".format(e))
            response_data = {'message': "Data not updated", 'status': False}
            response_status = status.HTTP_400_BAD_REQUEST
        return Response({'data': response_data, 'status': response_status})

    def get_transaction_data_object(self, transaction_id):
        transaction_obj = None
        if transaction_id:
            try:
                transaction_obj = (
                    YGPayClientTransactionData.objects.get(
                        transaction_id=transaction_id))
            except YGPayClientTransactionData.DoesNotExist:
                transaction_obj = None
        return transaction_obj
