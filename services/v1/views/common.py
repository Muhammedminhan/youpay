import hmac
import hashlib
import logging

from django.db import transaction
from rest_framework import status
from datetime import datetime, timezone

from core.constants import (
    PAYMENT_GATEWAY_CHECKOUTPG, PAYMENT_GATEWAY_HAPPYCREDITS,
    PURCHASE_PLATFORM_IOS,
    PURCHASE_PLATFORM_ANDROID, PAYMENT_GATEWAY_B2CPAYBACK
)
from core.messages import (
    ERROR_MISSING_FIELDS, IS_SUCCESS
)
from core.messages import (
    REDIRECT_URL,
    TRANSACTION_MSG,
    IS_REDIRECT
)
from core.models import PaymentConfiguration
from integrations.constants import CHECKOUTPG_SUCCESS_RESPONSE_CODE
from integrations.models import AdditionalChargeConfiguration
from integrations.models import PaymentGateway
from payments.constants import (PAYMENT_STATUS_PAID, YOUGOTAGIFT_UAE,
                                YOUGOTAGIFT_KSA, PAYMENT_END_STATUS_LIST,
                                PAYMENT_STATUS_AUTHORIZED,
                                PAYMENT_STATUS_REJECTED_RETRY,
                                PAYMENT_METHOD_QITAF,
                                PAYMENT_METHOD_QITAFAND_CARD,
                                PAYMENT_METHOD_NEQATY_AND_CARD,
                                PAYMENT_METHOD_NEQATY, PAYMENT_METHOD_ADCB,
                                PAYMENT_METHOD_TOUCHPOINTS_AND_CARD,
                                PAYMENT_METHOD_TOUCHPOINTS,
                                PAYMENT_METHOD_MOKAFAA,
                                PAYMENT_METHOD_MOKAFAA_AND_CARD,
                                PAYMENT_METHOD_ANB,
                                PAYMENT_METHOD_ANB_AND_CARD,
                                PAYMENT_METHOD_PAYPAL)
from payments.models import (YouPayTransactionData, AdditionalCharge)
from payments.serializers.youpay_payments import (
    YouPayTransactionDataSerializer
)
from services.constants import (CURRENCY_UAE, CURRENCY_KSA,
                                SOFT_DECLINE_RESPONSE_CODE_STARTSWITH,
                                TPAY_PUBLIC_KEY, TPAY_PRIVATE_KEY)
from services.models import APIClient, OfferDetails

logger = logging.getLogger(__name__)


def get_saved_fields(saved_fields, data_dict, transaction_obj):
    for key, value in data_dict.items():
        if str(value) not in ['', 'None']:
            transaction_obj.__dict__[key] = value
            saved_fields.append(key)

    return saved_fields


class YouPayTransactionCRUD(object):
    """
    YouPay Transaction Data CRUD Operations will be here
    """

    def __init__(self):
        self.saved_fields = []


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
                transaction_obj = (
                    YouPayTransactionData.objects.select_for_update().get(
                        happy_credit_reference=payment_reference))
                return transaction_obj
            except YouPayTransactionData.DoesNotExist:
                logger.error("Unable to find youpay transaction object for {}"
                             "".format(payment_reference))
                return None

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

    def get_youpay_transaction_data(self, transaction_id):
        with transaction.atomic():
            try:
                transaction_obj = (
                    YouPayTransactionData.objects.select_for_update().get(
                        transaction_id=transaction_id))
                return transaction_obj
            except YouPayTransactionData.DoesNotExist:
                logger.error("Unable to find youpay transaction object with "
                             "transaction id {}".format(transaction_id))
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
        data_dict['is_gcc_card'] = data.get('is_gcc_card', None)
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
        data_dict['is_full_redemption'] = data.get('is_full_redemption', None)
        data_dict['point_collection_enabled'] = data.get(
            'point_collection_enabled', None)
        data_dict['points_collected_mobile_number'] = data.get(
            'points_collected_mobile_number', None)
        data_dict['points_collected_cic_number'] = data.get(
            'points_collected_cic_number', None)
        data_dict['points_redeemed_mobile_number'] = data.get(
            'points_redeemed_mobile_number', None)
        data_dict['point_program'] = data.get('point_program', None)
        data_dict['earn_reference'] = data.get('earn_reference', None)
        data_dict['redemption_partner'] = data.get('redemption_partner', None)

        data_dict['additional_vat'] = data.get('additional_vat', None)
        data_dict['additional_processing_fee'] = (
            data.get('additional_processing_fee', None))
        data_dict['additional_processing_fee_vat'] = (
            data.get('additional_processing_fee_vat', None))
        data_dict['additional_total_amount'] = (
            data.get('additional_total_amount', None))

        data_dict['credit_balance_amount'] = data.get('credit_balance_amount',
                                                      None)
        data_dict['available_credit_balance'] = data.get(
            'available_credit_balance', None)

        data_dict['is_fraud'] = data.get('is_fraud', None)
        data_dict['is_flagged'] = data.get('is_flagged', None)
        data_dict['retry_count'] = data.get('retry_count', None)

        data_dict['currency'] = data.get('currency', None)
        data_dict['is_payment_verified'] = data.get('is_payment_verified',
                                                    None)
        data_dict['maximum_redeemable_points'] = data.get(
            'maximum_redeemable_points', None)
        data_dict['minimum_redeemable_points'] = data.get(
            'minimum_redeemable_points', None)
        data_dict['amount_conversion_rate'] = data.get(
            'amount_conversion_rate', None)
        data_dict['citi_order_id'] = data.get('citi_order_id', None)
        data_dict['citi_phone_number'] = data.get('citi_phone_number', None)
        data_dict['qitaf_phone_number'] = data.get('qitaf_phone_number', None)
        data_dict['is_qitaf_enabled'] = data.get('is_qitaf_enabled', None)
        data_dict['earned_point'] = data.get('earned_point', None)
        data_dict['gateway_charge'] = data.get('gateway_charge', 0)
        data_dict['brand_calculations'] = data.get('brand_calculations', None)
        data_dict['udf1'] = data.get('udf1', None)

        if data_dict['payment_method'] in [PAYMENT_METHOD_QITAF,
                                           PAYMENT_METHOD_QITAFAND_CARD,
                                           PAYMENT_METHOD_NEQATY_AND_CARD,
                                           PAYMENT_METHOD_NEQATY,
                                           PAYMENT_METHOD_MOKAFAA,
                                           PAYMENT_METHOD_MOKAFAA_AND_CARD,
                                           PAYMENT_METHOD_ANB,
                                           PAYMENT_METHOD_ANB_AND_CARD,
                                           PAYMENT_METHOD_PAYPAL
                                           ]:
            # updating amount and someother informations for qitaf
            amount = data.get('amount', None)
            service_fee = data.get('service_fee', None)
            base_amount = data.get('base_amount', None)
            vat_amount = data.get('VAT_amount', None)

            data_dict['amount'] = amount
            data_dict['service_fee'] = service_fee
            data_dict['base_amount'] = base_amount
            data_dict['VAT_amount'] = vat_amount

        if data_dict['payment_status'] in PAYMENT_END_STATUS_LIST:
            data_dict['settlement_entity'] = self.get_settlement_entity(
                payment_gateway=data_dict['payment_gateway'],
                currency=data_dict['currency'],
                transaction_id=transaction_id)

        try:
            transaction_obj = self.get_youpay_transaction_data(transaction_id)
            if transaction_obj:
                self.saved_fields = [
                    'updated_at'
                ]
                self.saved_fields = get_saved_fields(self.saved_fields,
                                                data_dict,
                                                transaction_obj)
                if data_dict.get('is_full_redemption') == False:
                    transaction_obj.is_full_redemption = False
                    self.saved_fields.append('is_full_redemption')

                self.update_point_program_on_transaction_obj(
                    transaction_obj)

                transaction_obj.save(update_fields=self.saved_fields)
                logger.info(
                    "Transaction object updated successfully for {}, status :"
                    "{}, updated fields {}".format(
                        transaction_id, transaction_obj.payment_status,
                        self.saved_fields))

                if (transaction_obj.payment_status == PAYMENT_STATUS_PAID
                        and not transaction_obj.gateway_charge):
                    from payments.tasks import (
                        update_calculated_gateway_charges)
                    update_calculated_gateway_charges.delay(
                        transaction_id=transaction_id)
                return True
            else:
                logger.error("unable to find the transaction object for {}"
                             "".format(transaction_id))
                return False
        except Exception as e:
            logger.error("Unable to update the transaction object, {0}"
                         "".format(str(e)))
            return False

    def update_point_program_on_transaction_obj(self, transaction_obj):
        
        if transaction_obj.payment_status == PAYMENT_STATUS_PAID:
            if transaction_obj.payment_gateway == PAYMENT_GATEWAY_B2CPAYBACK:

                """ADCB point program handler"""
                if (transaction_obj.payment_method in
                        [PAYMENT_METHOD_TOUCHPOINTS,
                         PAYMENT_METHOD_TOUCHPOINTS_AND_CARD]):
                    transaction_obj.point_program = PAYMENT_METHOD_ADCB
                    self.saved_fields.append("point_program")
            else:
                logger.info(
                    f"Not {PAYMENT_GATEWAY_B2CPAYBACK}, "
                    f"{type(transaction_obj.payment_gateway)}")

            logger.info(
                f"update_point_program_on_transaction_obj payment_status : "
                f"{transaction_obj.payment_status}, payment_gateway:"
                f" {transaction_obj.payment_gateway}, payment_method: "
                f"{transaction_obj.payment_method}, "
                f"point_program :{transaction_obj.point_program},"
                f"transaction_id :{transaction_obj.transaction_id} ")

        return transaction_obj

    def get_settlement_entity(self, **kwargs):
        """
        This method is used to get settlement entity

        If the currency is AED then the entity value will be Yougotagift UAE

        If the currency is SAR then the entity value will be Yougotagift KSA

        For Happy Credits → It will be blank.
        """
        transaction_id = kwargs.get('transaction_id', None)
        currency = kwargs.get('currency', None)
        payment_gateway = kwargs.get('payment_gateway', None)

        if (payment_gateway is None or payment_gateway == '' or
                currency is None or currency == ''):
            transaction_obj = self.get_youpay_transaction_data(transaction_id)
            currency = transaction_obj.currency
            if payment_gateway is None or payment_gateway == '':
                payment_gateway = transaction_obj.payment_gateway

        settlement_entity = None
        if payment_gateway == PAYMENT_GATEWAY_HAPPYCREDITS:
            settlement_entity = None
            return settlement_entity
        elif currency == CURRENCY_UAE:
            settlement_entity = YOUGOTAGIFT_UAE
        elif currency == CURRENCY_KSA:
            settlement_entity = YOUGOTAGIFT_KSA
        else:
            logger.error("Settlement entity not found for currency {}"
                         "".format(currency))
        return settlement_entity

    def create_offer_details(self, data):
        """
        Creates an OfferDetails record with the given data.

        Parameters:
            data (dict): Contains 'invoice_id', 'offer_details', and 'client'.
        """
        try:
            OfferDetails.objects.create(
                invoice_id=data.get('invoice_id'),
                offer_details=data.get('offer_details'),
                client=data.get('client')
            )
        except Exception as e:
            logger.error("Error in creating offer details object  "
                         "{}".format(str(e)))

    def get_offer_details(self, transaction_obj):
        """
        Retrieves offer details for a given transaction.

        Parameters:
            transaction_obj: The transaction instance.

        Returns:
            dict or None: Offer details if found, else None.
        """
        invoice_id = transaction_obj.invoice_id
        client = transaction_obj.api_client

        try:
            if not transaction_obj.is_offer_applicable:
                return None
            offer_detail_obj = OfferDetails.objects.filter(
                invoice_id=invoice_id, client=client).last()

            offer_details = offer_detail_obj.offer_details
            if offer_details:
                return offer_details
            else:
                logger.error(
                    "Offer details not found for transaction {}".format(
                        transaction_obj.transaction_id))
                return None
        except Exception as e:
            logger.error("Error in getting offer details for {} ".format(
                transaction_obj.transaction_id))
            return None


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
                    return True, client
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
    if ((str(response_code).startswith(
            SOFT_DECLINE_RESPONSE_CODE_STARTSWITH) or response_code is None) and
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
            TRANSACTION_MSG: transaction_message,
            IS_SUCCESS: False
        }
        return False, response_data

    if youpay_transaction.payment_status == PAYMENT_STATUS_REJECTED_RETRY:
        # Mainly occurs for tabbypg, this will redirect to FE payment page

        response_data = {
            IS_REDIRECT: False,
            REDIRECT_URL: None,
            TRANSACTION_MSG: transaction_message,
            IS_SUCCESS: False
        }
        return False, response_data

    if (youpay_transaction.payment_status == PAYMENT_STATUS_PAID or
            (str(response_code) == str(
                CHECKOUTPG_SUCCESS_RESPONSE_CODE) and str(
                youpay_transaction.payment_status).lower() == (
                     PAYMENT_STATUS_AUTHORIZED))):
        redirect_url = (youpay_transaction.success_url +
                        '?transaction_id=' + transaction_id)

        response_data = {
            IS_REDIRECT: True,
            REDIRECT_URL: redirect_url,
            TRANSACTION_MSG: transaction_message,
            IS_SUCCESS: True
        }
        return True, response_data
    else:
        redirect_url = (youpay_transaction.failure_url +
                        '?transaction_id=' + transaction_id)
        response_data = {
            IS_REDIRECT: True,
            REDIRECT_URL: redirect_url,
            TRANSACTION_MSG: transaction_message,
            IS_SUCCESS: False
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


def add_payment_gateway_info_in_url(**kwargs):
    """
    Method to add payment gateway info in url
    sample : https://fe-domain.com/language/path/+ params + hubcode
    """
    try:

        transaction_data = kwargs.get('transaction_data', None)
        app_config = kwargs.get('app_config', None)
        params = kwargs.get('params', None)
        code = kwargs.get('code', None)

        language = transaction_data.get('language', None)
        platform = transaction_data.get('platform', None)

        frontend_domain = app_config.front_end_domain
        path = app_config.redirect_path
        params = params + "&gty=" + code

        if platform in [PURCHASE_PLATFORM_IOS, PURCHASE_PLATFORM_ANDROID]:
            params = params + "&platform=app"

        url = (
            "{}{}/{}{}".format(frontend_domain, language, path, params))
        return url
    except Exception as e:
        logger.error(
            "Exception occurred while adding payment gateway info "
            "in url : {}".format(str(e)))
        return None


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

def get_processing_charge(currency, charge_type, payment_gateway,
                          payment_method):
    """
    Method to get additional charge configuration.
    """
    try:
        payment_config = PaymentConfiguration.objects.get(
            payment_method=payment_method,
            payment_gateway__code=payment_gateway)
    except PaymentConfiguration.DoesNotExist:
        logger.error(
            f"PaymentConfiguration not found for method: {payment_method}")
        return None, None

    try:
        additional_charge_obj = AdditionalChargeConfiguration.objects.get(
            currency__iso_code=currency, charge_type=charge_type,
            payment_option=payment_config, is_active=True)
    except AdditionalChargeConfiguration.DoesNotExist:
        logger.error(
            f"AdditionalChargeConfiguration not found for charge_type: "
            f"{charge_type}, currency: {currency}")
        return None, None

    return additional_charge_obj.percentage, additional_charge_obj.VAT_percentage

def generate_tpay_epoch_timespan():
    """
        Generates the current timestamp in TPay-required epoch format.
    """
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    delta = now - epoch

    days = delta.days
    seconds = delta.seconds
    microseconds = delta.microseconds

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    fraction = f"{microseconds * 10:07d}"

    return f"{days}.{hours:02}:{minutes:02}:{secs:02}.{fraction}"

def generate_script_signature():
    """
        Generates the script signature required to load the TPay checkout script.
    """
    epoch_time = generate_tpay_epoch_timespan()

    digest = hmac.new(
        TPAY_PRIVATE_KEY.encode(),
        epoch_time.encode(),
        hashlib.sha256
    ).hexdigest()

    return epoch_time, f"{TPAY_PUBLIC_KEY}:{digest}"

def generate_checkout_signature(merchant_template_key, operator_code,
        product_catalog, product_price, language, order_info, redirect_url):
    """
        Generates the checkout signature for TPay One-Time Payment.
    """
    message = (
        merchant_template_key +
        operator_code +
        product_catalog +
        str(product_price) +
        str(language) +
        order_info +
        redirect_url
    )

    digest = hmac.new(
        TPAY_PRIVATE_KEY.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    return f"{TPAY_PUBLIC_KEY}:{digest}"
