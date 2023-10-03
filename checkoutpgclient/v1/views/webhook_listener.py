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
from core.utils import checkout_decline_check
from integrations.common import WebhookDataFormat
from integrations.v1.gateway_clients.checkoutpg import CheckoutpgManager
from payments.models import YouPayTransactionData

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


class WebhookListener(APIView, WebhookDataFormat):
    authentication_classes = (
        YoupayAuthentication,
    )

    def post(self, request):
        request_data = json.loads(request.data)
        transaction_id = None
        invoice_id = None
        payment_status = None
        payment_reference = None
        track_info = None
        is_youpay_updated = False
        try:
            checkout_obj = CheckoutpgManager()

            invoice_pk = self.get_invoice_id(
                str(request_data.get('payment_reference', None)))

            logger.info("Checkoutpg webhook received {} for invoice :{}"
                        "".format(request_data, invoice_pk))

            payment_reference = request_data.get('payment_reference', None)
            transaction_obj = get_transaction_object(payment_reference)
            payment_status = str(request_data.get('status', None))

            track_info = "Webhook received "

            if transaction_obj:
                transaction_obj.approved = request_data.get('approved')
                transaction_obj.status = payment_status
                transaction_obj.auth_code = str(
                    request_data.get('auth_code'))
                transaction_obj.response_summary = str(
                    request_data.get('response_summary'))
                transaction_obj.api_response_data = request_data.get(
                    'api_response_data')
                transaction_obj.payment_reference = str(
                    request_data.get('payment_reference'))
                transaction_obj.is_fraud = request_data.get('is_fraud')
                transaction_obj.is_flagged = request_data.get('is_flagged')
                transaction_obj.payment_id = request_data.get('payment_id',
                                                              None)
                transaction_obj.financial_action_response_data = (
                    request_data.get('financial_action_response_data', None))

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
                transaction_obj.issuer_bank = self.get_issuer_bank(
                    request_data.get('api_response_data'))
                transaction_obj.three_ds_check = self.get_three_ds(
                    request_data.get('api_response_data'))
                transaction_obj.cvv_check = self.get_cvv_check(
                    request_data.get('api_response_data'))
                transaction_obj.save()
                track_info = track_info + ", checkoutpg client updated"
                data_to_update = self.prepare_youpay_transaction_update_data(
                    request_data, payment_reference)

                transaction_id = data_to_update.get('transaction_id')

                if data_to_update:
                    is_youpay_updated = checkout_obj.update_youpay_transaction_data(
                        data_to_update)
                    track_info = (track_info + ", youpay update status :" +
                                  str(is_youpay_updated))
            else:
                transaction_obj = TransactionData.objects.create(
                    invoice_id=invoice_pk,
                    order_reference=request_data.get('order_reference',
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
                    status=payment_status,
                    auth_code=str(request_data.get('auth_code', None)),
                    response_summary=str(
                        request_data.get('response_summary', None)),
                    idempotency_key=str(
                        request_data.get('idempotency_key')),
                    is_fraud=request_data.get('is_fraud'),
                    is_flagged=request_data.get('is_flagged'),
                    card_bin=request_data.get('card_bin', None),
                    card_last4=request_data.get('card_last4', None),
                    payment_method=request_data.get('payment_method',
                                                    PAYMENT_METHOD_CARD),
                    payment_scheme=request_data.get('payment_scheme',
                                                    None),
                    payment_id=request_data.get('payment_id',
                                                None),
                    financial_action_response_data=request_data.get(
                        'financial_action_response_data', None),
                    issuer_bank=self.get_issuer_bank(request_data.get(
                        'api_response_data')),
                    three_ds_check=self.get_three_ds(request_data.get(
                        'api_response_data')),
                    cvv_check=self.get_cvv_check(request_data.get(
                        'api_response_data'))
                )
                track_info = (track_info +
                              ",New Record created in checkoutpg client")

            response_data = {'message': "Checkout webhook listener "
                                        "successfully processed data",
                             'status': True}

            return self.pg_response('HTTP_200_OK', data=response_data)
        except Exception as e:
            logger.error("Checkoutpg webhook failed with error {}".format(e),
                         exc_info=True)
            response_data = {'message': "Data not  updated", 'status': False}
            track_info = track_info + ", Exception occurred :" + str(e)
            return self.pg_response('HTTP_500_INTERNAL_SERVER_ERROR',
                                    data=response_data)
        finally:
            logger.info(
                "Checkoutpg Webhook received for transaction id :{}, "
                "payment_reference :{}, invoice :{}, status :{}, request data"
                " :{}, is_youpay_updated :{}, Track info : {}".format(
                    transaction_id, payment_reference, invoice_id,
                    payment_status, request_data, is_youpay_updated,
                    track_info))

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

    def prepare_youpay_transaction_update_data(self, request_data,
                                               payment_reference):
        request_data['response_code'] = request_data.get(
            'checkout_response_code', None)

        payment_status, is_payment_verified = checkout_decline_check(
            request_data)
        try:
            print("\n\npayment reference ", payment_reference)
            transaction_obj = (
                self.get_youpay_transaction_data_with_payment_reference(
                    payment_reference))
            if transaction_obj:
                data_to_update = {
                    'transaction_id': transaction_obj.transaction_id,
                    "payment_status": (
                        payment_status.lower() if payment_status else None),
                    "payment_reference": request_data.get("reference"),
                    "approved": request_data.get("approved"),
                    "response_summary": request_data.get("response_summary"),
                    "card_bin": request_data.get("card_bin"),
                    "card_last4": request_data.get("card_last4"),
                    'payment_scheme': request_data.get("payment_scheme"),
                    'is_gcc_card': request_data.get("is_gcc_card"),
                    'card_issuer_country': request_data.get(
                        "card_issuer_country"),
                    'is_fraud': request_data.get("is_fraud"),
                    'is_flagged': request_data.get("is_flagged"),
                }
                return data_to_update
            else:
                logger.info(
                    "Transaction object not found for payment reference "
                    "{}".format(payment_reference))
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
            logger.info(
                "Unable to find youpay transaction object with payment"
                "_reference {}".format(payment_reference))
            return None
