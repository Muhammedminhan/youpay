import decimal
import json
import logging

from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from checkoutpgclient.constants import PAYMENT_METHOD_CARD
from checkoutpgclient.libs.authentication import YoupayAuthentication
from checkoutpgclient.models import TransactionData


logger = logging.getLogger(__name__)


def get_transaction_object(payment_reference):
    with transaction.atomic():
        transaction_obj = None
        if payment_reference:
            try:
                transaction_obj = (
                    TransactionData.objects.select_for_update().get(
                        payment_reference=payment_reference))
            except TransactionData.DoesNotExist:
                transaction_obj = None
        return transaction_obj


class WebhookListener(APIView):
    authentication_classes = (
        YoupayAuthentication,
    )

    def post(self, request):
        request_data = json.loads(request.data)
        try:
            invoice_pk = self.get_invoice_id(
                str(request_data.get('payment_reference', None)))
            logger.info("Checkoutpg webhook received for invoice {}".format(
                invoice_pk))

            lock_name = 'lock:WebhookListener:invoice_%d' % (int(invoice_pk),)

            transaction_obj = get_transaction_object(
                request_data.get(
                    'payment_reference', None))

            if transaction_obj:
                logger.info(
                    "In Webhook listner payment scheme for invoice {0}"
                    " is {1}".format(invoice_pk,
                                     transaction_obj.payment_scheme))
                transaction_obj.approved = request_data.get('approved')
                transaction_obj.status = str(request_data.get('status'))
                transaction_obj.auth_code = str(
                    request_data.get('auth_code'))
                transaction_obj.response_summary = str(
                    request_data.get('response_summary'))
                transaction_obj.api_response_data = request_data.get(
                    'api_response_data')
                transaction_obj.payment_reference = str(
                    request_data.get('payment_reference'))
                transaction_obj.is_fraud = request_data.get('is_fraud',
                                                            False)
                transaction_obj.is_flagged = request_data.get(
                    'is_flagged',
                    False)
                # Update the card bin & last4 if it is present in data
                card_bin = request_data.get('card_bin', None)
                card_last4 = request_data.get('card_last4', None)

                if card_bin:
                    transaction_obj.card_bin = card_bin
                if card_last4:
                    transaction_obj.card_last4 = card_last4
                transaction_obj.payment_scheme = request_data.get(
                    'payment_scheme',
                    None)

                transaction_obj.save()
            else:
                transaction_obj = TransactionData.objects.create(
                    invoice_id=invoice_pk,
                    order_reference=request_data.get('idempotency_key',
                                                     None),
                    amount=decimal.Decimal(
                        str(request_data.get('amount', None))),
                    currency=request_data.get('currency', None),
                    customer_name=
                    request_data.get('customer_name', None),
                    customer_email=
                    request_data.get('customer_email', None),
                    payment_reference=request_data.get(
                        'payment_reference', None),
                    request_source=request_data.get('request_source',
                                                    None),
                    api_request_data=
                    request_data.get('api_request_data', None),
                    api_response_data=
                    request_data.get('api_response_data', None),
                    is_notification=request_data.get('is_notification',
                                                     None),
                    approved=request_data.get('approved', None),
                    status=str(request_data.get('status', None)),
                    auth_code=str(request_data.get('auth_code', None)),
                    response_summary=str(
                        request_data.get('response_summary', None)),
                    idempotency_key=str(
                        request_data.get('idempotency_key')),
                    is_fraud=request_data.get('is_fraud', False),
                    is_flagged=request_data.get('is_flagged', False),
                    card_bin=request_data.get('card_bin', None),
                    card_last4=request_data.get('card_last4', None),
                    payment_method=request_data.get('payment_method',
                                                    PAYMENT_METHOD_CARD),
                    payment_scheme=request_data.get('payment_scheme',
                                                    None)
                )

            logger.info("Payment scheme set is {0} for transaction"
                        " {1}".format(transaction_obj.payment_scheme,
                                      transaction_obj.payment_reference))
            response_data = {'message': "Checkout webhook listener "
                                        "successfully processed data",
                             'status': True}
            logger.info("Checkoutpg webhook successfully processed "
                        "for invoice {}".format(invoice_pk))
            return self.pg_response('HTTP_200_OK', data=response_data)
        except Exception as e:
            logger.error("Checkoutpg webhook failed with error {}".format(e))
            response_data = {'message': "Data not  updated", 'status': False}
            return self.pg_response('HTTP_500_INTERNAL_SERVER_ERROR',
                                    data=response_data)

    def get_invoice_id(self, paymentrefernce):
        paymentrefernce = paymentrefernce.split('-')
        invoice_id = paymentrefernce[2].split('|')
        invoice_id = invoice_id[0]
        return invoice_id

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
