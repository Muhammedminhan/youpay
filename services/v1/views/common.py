import logging

from rest_framework import status

from core.messages import ERROR_MISSING_FIELDS
from core.messages import (
    REDIRECT_URL, TRANSACTION_MSG, IS_REDIRECT
)
from integrations.models import PaymentGateway
from payments.constants import PAYMENT_STATUS_PAID
from payments.models import YouPayTransactionData
from payments.serializers.youpay_payments import (
    YouPayTransactionDataSerializer
)
from services.constants import RESPONSE_CODE_LIST
from services.models import APIClient

logger = logging.getLogger(__name__)


def get_saved_fields(saved_fields, data_dict, transaction_obj):
    for key, value in data_dict.items():
        if value:
            transaction_obj.__dict__[key] = value
            saved_fields.append(key)

    return saved_fields


class YouPayTransactionCRUD(object):
    """
    YouPay Transaction Data CRUD Operations will be here
    """

    def create_youpay_transaction_data(self, request):
        serializer = YouPayTransactionDataSerializer(data=request)
        if serializer.is_valid():
            serializer.save()
            return {"status": status.HTTP_201_CREATED,
                    "data": serializer.data, "message": "created"}
        else:
            errors = serializer.errors.keys()
            missing_fields = ', '.join(
                ["".join(missing) for missing in errors])
            message = "{}{}".format(ERROR_MISSING_FIELDS, missing_fields)
            return {"status": status.HTTP_400_BAD_REQUEST,
                    "data": serializer.errors, "message": message}

    def get_youpay_transaction_data(self, transaction_id):
        try:
            transaction_obj = YouPayTransactionData.objects.get(
                transaction_id=transaction_id)
            return transaction_obj
        except YouPayTransactionData.DoesNotExist:
            logger.error("Unable to find youpay transaction object for {}"
                         "".format(transaction_id))
            return None

    def update_youpay_transaction_data(self, data):
        """Method to update youpay transaction data"""
        data_dict = {}
        transaction_id = data.get('transaction_id')
        data_dict['payment_reference'] = data.get('payment_reference', None)
        data_dict['payment_status'] = data.get('payment_status', None)
        data_dict['payment_gateway'] = data.get('payment_gateway', None)
        data_dict['channel_code'] = data.get('channel_code', None)
        data_dict['payment_method'] = data.get('payment_method', None)
        data_dict['payment_scheme'] = data.get('payment_scheme', None)
        data_dict['is_gcc_card'] = data.get('is_gcc_card', False)
        data_dict['card_bin'] = data.get('card_bin', None)
        data_dict['card_last4'] = data.get('card_last4', None)
        data_dict['card_issuer_country'] = data.get('card_issuer_country',
                                                    None)
        data_dict['approved'] = data.get('approved', None)
        data_dict['response_summary'] = data.get('response_summary', None)

        try:
            transaction_obj = self.get_youpay_transaction_data(transaction_id)
            if transaction_obj:
                saved_fields = ['updated_at']
                saved_fields = get_saved_fields(saved_fields, data_dict,
                                                transaction_obj)
                transaction_obj.save(update_fields=saved_fields)
            else:
                logger.error("unable to find the transaction object for {}"
                             "".format(transaction_id))
        except Exception as e:
            logger.error("Unable to update the transaction object, {0}"
                         "".format(str(e)))


class ClientValidator(object):
    """
    Client Validation will be here
    """

    def validate_client(self, request):
        client_id = ''
        api_key = request.META.get('HTTP_X_API_KEY', None)
        if api_key:
            try:
                client = APIClient.objects.get(api_key=api_key)
                if client:
                    client_id = client.pk
                    return True, client_id
                return False, client_id
            except Exception as e:
                logger.info("Exception occurred when validating the client {}"
                            .format(str(e)))
                return False, client_id
        return False, client_id


class PaymentRequestDataValidator(object):
    """
    Payment Request Data Validation will be here
    """

    def validate_payment_request_data(self, request):
        if request.data.get("payment"):
            if request.data["payment"].get("ip"):
                return True
            return False
        return False


def is_redirect(transaction_id, transaction_message):
    logger.info(
        "is_redirect called for transaction_id: {}\nPayment Gateway Response:"
        "{}".format(transaction_id, transaction_message))
    response_data = None
    youpay = YouPayTransactionCRUD()
    youpay_transaction = youpay.get_youpay_transaction_data(transaction_id)

    is_fraud = transaction_message.get('is_fraud', False)

    response_code = transaction_message.get('response_code', None)
    if response_code in RESPONSE_CODE_LIST or is_fraud:
        redirect_url = None
        response_data = {
            IS_REDIRECT: False,
            REDIRECT_URL: redirect_url,
            TRANSACTION_MSG: transaction_message
        }
        return True, response_data

    if youpay_transaction.payment_status == PAYMENT_STATUS_PAID:

        response_data = {
            IS_REDIRECT: True,
            REDIRECT_URL: youpay_transaction.success_url,
            TRANSACTION_MSG: transaction_message
        }
        return True, response_data
    else:
        response_data = {
            IS_REDIRECT: True,
            REDIRECT_URL: youpay_transaction.failure_url,
            TRANSACTION_MSG: transaction_message
        }
        return False, response_data


def get_api_key_from_payment_gateway(hubcode):
    """Method to get api key from payment gateway"""
    try:
        payment_gateway = PaymentGateway.objects.get(code=hubcode)
        return payment_gateway.api_key
    except PaymentGateway.DoesNotExist:
        logger.error(
            "Unable to find payment gateway for hubcode '{}' ".format(
                hubcode))
        return None


def add_payment_gateway_info_in_url(url, params, code):
    """
    Method to add payment gateway info in url
    sample : https://fe-domain.com/payment-response/+ params + hubcode
    """
    url = url + params + "&payment_gateway=" + code
    return url
