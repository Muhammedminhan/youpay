import logging

from django.utils.decorators import decorator_from_middleware, classonlymethod
from rest_framework import status
from django.db import transaction

from core.constants import (
    PAYMENT_GATEWAY_CHECKOUTPG, PAYMENT_GATEWAY_TABBYPG,
    PAYMENT_GATEWAY_B2CPAYBACK)
from core.messages import ERROR_MISSING_FIELDS
from core.messages import (
    REDIRECT_URL, TRANSACTION_MSG, IS_REDIRECT
)
from core.middlewares.workflow_middleware import PaymentStatusCheckMiddleware
from integrations.models import PaymentGateway
from payments.constants import PAYMENT_STATUS_PAID
from payments.models import (YouPayTransactionData, AdditionalCharge)
from payments.serializers.youpay_payments import (
    YouPayTransactionDataSerializer
)
from services.constants import RESPONSE_CODE_LIST
from services.models import APIClient

logger = logging.getLogger(__name__)

payment_status_check = decorator_from_middleware(
    PaymentStatusCheckMiddleware)


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

    def get_transaction_data_by_credit_reference(self, payment_reference):
        """
        Method used to return transaction object for selected happy credits
        reference
        """
        with transaction.atomic():
            try:
                transaction_obj = YouPayTransactionData.objects.get(
                    happy_credit_reference=payment_reference)
                return transaction_obj
            except YouPayTransactionData.DoesNotExist:
                logger.error("Unable to find youpay transaction object for {}"
                             "".format(payment_reference))
                return None

    def get_youpay_transaction_data(self, transaction_id):
        with transaction.atomic():
            try:
                transaction_obj = (
                    YouPayTransactionData.objects.select_for_update().get(
                    transaction_id=transaction_id))
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
        data_dict['happy_credit_reference'] = (
            data.get('happy_credit_reference', None))
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
        data_dict['name_on_card'] = data.get('name_on_card', None)

        data_dict['redeemed_amount'] = data.get('redeemed_amount', None)
        data_dict['redeemed_points'] = data.get('redeemed_points', None)
        data_dict['payable_amount'] = data.get('payable_amount', None)
        data_dict['available_amount'] = data.get('available_amount', None)
        data_dict['available_points'] = data.get('available_points', None)

        data_dict['additional_vat'] = data.get('additional_vat', None)
        data_dict['additional_processing_fee'] = (
            data.get('additional_processing_fee', None))
        data_dict['additional_processing_fee_vat'] = (
            data.get('additional_processing_fee_vat', None))
        data_dict['additional_total_amount'] = (
            data.get('additional_total_amount', None))
        data_dict['is_full_redemption'] = data.get('is_full_redemption',
                                                   None)

        data_dict['credit_balance_amount'] = data.get('credit_balance_amount',
                                                      None)
        data_dict['available_credit_balance'] = data.get(
            'available_credit_balance', None)

        data_dict['is_fraud'] = data.get('is_fraud', None)
        data_dict['is_flagged'] = data.get('is_flagged', None)
        data_dict['retry_count'] = data.get('retry_count', None)
        try:
            transaction_obj = self.get_youpay_transaction_data(transaction_id)
            if transaction_obj:
                saved_fields = [
                    'updated_at'
                ]
                saved_fields = get_saved_fields(saved_fields,
                                                data_dict,
                                                transaction_obj)
                if data_dict.get('is_full_redemption') == False:
                    transaction_obj.is_full_redemption = False
                    saved_fields.append('is_full_redemption')
                transaction_obj.save(update_fields=saved_fields)
                logger.info(
                    "Transaction object updated successfully for {}"
                    "".format(transaction_id))

                if (transaction_obj.payment_status == PAYMENT_STATUS_PAID
                        and not transaction_obj.gateway_charge):
                    from payments.tasks import (
                        update_calculated_gateway_charges)
                    update_calculated_gateway_charges.delay(
                        transaction_id=transaction_id)
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
        "is_redirect called for transaction_id: {} Payment Gateway Response:"
        "{}".format(transaction_id, transaction_message))
    response_data = None
    youpay = YouPayTransactionCRUD()
    youpay_transaction = youpay.get_youpay_transaction_data(transaction_id)

    response_code = transaction_message.get('response_code', None)

    '''This check is applicable only for checkout payments'''
    if (response_code in RESPONSE_CODE_LIST and
            youpay_transaction.payment_gateway == PAYMENT_GATEWAY_CHECKOUTPG):
        '''We are setting the redirect url to none so in frontend it will 
        redirect to the payment page, which will give another try to the 
        customer in the current transaction, only for checkoutpg'''
        redirect_url = None
        logger.info("Checkout Response code checking for"
                    "transaction id {}".format(transaction_id))
        response_data = {
            IS_REDIRECT: False,
            REDIRECT_URL: redirect_url,
            TRANSACTION_MSG: transaction_message
        }
        return True, response_data

    if youpay_transaction.payment_status == PAYMENT_STATUS_PAID:

        redirect_url = (youpay_transaction.success_url +
                        '?transaction_id=' + transaction_id)

        response_data = {
            IS_REDIRECT: True,
            REDIRECT_URL: redirect_url,
            TRANSACTION_MSG: transaction_message
        }
        return True, response_data
    else:
        redirect_url = (youpay_transaction.failure_url +
                        '?transaction_id=' + transaction_id)
        response_data = {
            IS_REDIRECT: True,
            REDIRECT_URL: redirect_url,
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


def get_webhook_api_key_from_payment_gateway(hubcode):
    """Method to get webhook api key from payment gateway"""
    try:
        payment_gateway = PaymentGateway.objects.get(code=hubcode)
        return payment_gateway.webhook_api_key
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
    url = url + params + "&gty=" + code
    return url


def get_adcb_saved_fields(saved_fields, data_dict, transaction_obj):
    for key, value in data_dict.items():
        if value == 0 or value is False:
            transaction_obj.__dict__[key] = value
            saved_fields.append(key)

    return saved_fields


class AdditionalChargesUpdation(object):
    """
    YouPay Additional Charges CRUD Operations will be here
    """

    def get_additional_charges(self, transaction_id, payment_option):
        additional_charges = None
        try:
            additional_charges = AdditionalCharge.objects.get(
                payment_option=payment_option,
                transaction__transaction_id=transaction_id)
        except (AdditionalCharge.DoesNotExist, Exception):
            logger.info("No additional charge instance "
                        "found for {}".format(transaction_id))
        return additional_charges

    def create_additional_charges(self, data):
        try:
            AdditionalCharge.objects.create(
                transaction=data.get('transaction'),
                payment_option=data.get('payment_option'),
                additional_vat=data.get('new_vat'),
                additional_processing_fee=data.get('processing_fee'),
                additional_processing_fee_vat=data.get('processing_fee_vat'),
                additional_total_amount=data.get('total_amount')
            )
        except Exception as e:
            logger.error("Error in creating additional charge object for {} "
                         "{}".format(data.get('transaction').transaction_id,
                                     str(e)))


class PaymentStatusCheckMiddlewareMixin:
    @payment_status_check
    def dispatch(*args, **kwargs):
        return super().dispatch(*args, **kwargs)


def payment_status_check(class_view):
    def as_view(cls, **initkwargs):
        view = super(cls, cls).as_view(**initkwargs)
        view.payment_status_check = True
        return view

    return type(class_view.__name__, (class_view,), {
        'as_view': classonlymethod(as_view),
    })
