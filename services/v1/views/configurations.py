import logging
import random
import string

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

from core.response_messages import YouPayResponse
from core.utils import (decrypt_string, get_gateway_additional_fee,
                        encrypt_browser_value, decrypt_browser_value)
from integrations.models import PaymentGateway
from integrations.v1.gateway_clients.b2c_payback import B2CPaybackManager
from integrations.v1.gateway_clients.checkoutpg import CheckoutpgManager
from integrations.v1.gateway_clients.citi_service import CitiRewardsManager
from integrations.v1.gateway_clients.qitaf_service import QitafServiceManager
from integrations.v1.gateway_clients.tabbypg import TabbyPGManager
from payments.constants import (
    PAYMENT_STATUS_CANCELLED,
    PAYMENT_STATUS_PAID, PAYMENT_END_STATUS_LIST,
    PAYMENT_OPTION_CHECKOUT_APPLEPAY,
    PAYMENT_OPTION_PAYPAL, PAYMENT_OPTION_CITI_REWARDS, PAYMENT_OPTION_QITAF,
    PAYMENT_OPTION_TABBYPG, PAYMENT_OPTION_CHECKOUT_CARD,
    PAYMENT_OPTION_CHECKOUT_SAVED_CARD, PAYMENT_OPTION_ADCB,
)
from payments.models import YouPayTransactionData
from services.constants import (
    APPLEPAY_SUPPORTED_NETWORKS,
    APPLEPAY_MERCHANT_CAPABILITIES,
    APPLEPAY_LABEL,
)
from services.constants import TOKEN_TYPE_PAYPAL, TOKEN_TYPE_APPLEPAY
from services.v1.serializers.client_registrattion import (
    PaymentGatewaySerializer
)
from services.v1.views.utils import (
    get_announcements,
    get_session_id_from_header,
    get_country_for_configuration,
    get_client_for_configuration,
    get_payment_methods,
)

logger = logging.getLogger(__name__)


class ConfigViewSet(ViewSet):
    """
    Config viewset for getting payment gateways with transaction id
    """
    response_obj = YouPayResponse()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.list_failure_statuses = PAYMENT_END_STATUS_LIST

    def list(self, request):
        queryset = PaymentGateway.objects.all()
        serializer = PaymentGatewaySerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """
        Method for getting payment options and announcements
        session id is required in header
        transaction id is required in query params
        """

        session_id = get_session_id_from_header(request)

        decrypted_transaction_id = decrypt_string(pk)
        try:
            transaction = YouPayTransactionData.objects.get(
                transaction_id=decrypted_transaction_id)
            session_key = self.get_session_key(request)
            if transaction and self.check_browser_session(
                    transaction, session_key):
                logger.info(
                    "Initial session_key is {}  and browser value is {}"
                    "".format(session_key,
                              transaction.browser_value))
                # Redirect to success url if transaction is already paid
                if transaction.payment_status in self.list_failure_statuses:
                    return_response = self.retrieve_response(
                        payment_options=None,
                        checkoutpg_config=None,
                        transaction=transaction,
                        announcements_dict=None,
                        status_code=None
                    )
                    data = self.response_obj.get_success_dict(
                        code=self.response_obj.SUCCESS,
                        success_dict=return_response
                    )
                    return Response(data, status=status.HTTP_200_OK)

                # bypass session checking when api client is inactive
                if not transaction.api_client.validate_session:
                    session_id = transaction.session_id

                country = get_country_for_configuration(transaction)
                if not country:
                    message = "Not available for this country"
                    data = self.response_obj.get_404_message(message=message)

                    return Response(data,
                                    status=status.HTTP_404_NOT_FOUND)

                client = get_client_for_configuration(transaction)
                if not client:
                    message = "Client doesn't exists"
                    data = self.response_obj.get_404_message(
                        message=message)

                    return Response(data,
                                    status=status.HTTP_404_NOT_FOUND)

                payment_methods, partial_redemption_allowed_options = (
                    get_payment_methods(transaction, client, country))

                if transaction.session_id == session_id:
                    payment_options = payment_methods
                    announcements_dict = get_announcements(
                        transaction.platform)
                    api_client = {'color': client.color_code,
                                  'mobile_logo': get_mobile_logo_url(
                                      client),
                                  'logo': get_logo_url(client)}
                    paypal_config = self.get_paypal_config(
                        payment_options)
                    applepay_config = (
                        self.get_applepay_config(payment_options))
                    qitaf_config = self.get_qitaf_config(
                        payment_options, transaction,
                        partial_redemption_allowed_options,
                    )
                    citi_config = self.check_citi_allowed_denominations(
                        payment_options,
                        transaction)
                    tabbypg_config = self.get_tabby_conf(payment_options)
                    checkout_config = self.get_checkout_config(
                        payment_options, transaction)
                    adcb_config = self.get_adcb_config(
                        payment_options, transaction,
                        partial_redemption_allowed_options)

                    response_data = self.retrieve_response(
                        api_client=api_client,
                        payment_options=payment_options,
                        tabbypg_config=tabbypg_config,
                        checkoutpg_config=checkout_config,
                        adcb_config=adcb_config,
                        applepay_config=applepay_config,
                        transaction=transaction,
                        announcements_dict=announcements_dict,
                        paypal_config=paypal_config,
                        qitaf_config=qitaf_config,
                        citi_config=citi_config,
                        allow_aed_amount=(
                            transaction.api_client.allow_aed_converted_amount)
                    )

                    data = self.response_obj.get_success_dict(
                        code=self.response_obj.SUCCESS,
                        success_dict=response_data
                    )
                    return Response(data, status=status.HTTP_200_OK)
                else:
                    message = "Session expired or doesn't match"
                    data = self.response_obj.get_404_message(message=message)

                    return Response(data,
                                    status=status.HTTP_404_NOT_FOUND)
            else:
                data = self.response_obj.get_error_dict(
                    error_code=self.response_obj.UNKNOWN_ERR)
                return Response(data.get('errors'),
                                status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            logger.error(
                "Error occurred during config api call", exc_info=e)
            data = self.response_obj.get_404_message(message=str(e))
            return Response(
                data,
                status=status.HTTP_404_NOT_FOUND)
        finally:
            logger.info(
                "ConfigViewSet retrieve method called, Response data :"
                " {}".format(data))

    def retrieve_response(self, **kwargs):

        payment_options = kwargs.get('payment_options', None)
        api_client = kwargs.get('api_client', None)
        checkoutpg_config = kwargs.get('checkoutpg_config', None)
        tabbypg_config = kwargs.get('tabbypg_config', None)
        adcb_config = kwargs.get('adcb_config', None)
        transaction = kwargs.get('transaction', None)
        announcements_dict = kwargs.get('announcements_dict', None)
        applepay_config = kwargs.get('applepay_config', None)
        paypal_config = kwargs.get('paypal_config', None)
        qitaf_config = kwargs.get('qitaf_config', None)
        citi_config = kwargs.get('citi_config', None)
        aed_amount_flag = kwargs.get('allow_aed_amount', False)

        amount = None
        currency = None
        service_fee = None
        VAT_amount = None
        base_amount = None
        redirect_url = None

        cart_amount = None
        cart_currency = None
        cart_service_fee = None
        cart_base_amount = None
        cart_VAT_amount = None
        sessionkey = None

        if transaction:
            amount = transaction.amount
            currency = transaction.currency
            country_code = transaction.country_code
            service_fee = transaction.service_fee
            VAT_amount = transaction.VAT_amount
            base_amount = transaction.base_amount

            cart_amount = transaction.cart_amount
            cart_currency = transaction.cart_currency
            cart_service_fee = transaction.cart_service_fee
            cart_base_amount = transaction.cart_base_amount
            cart_VAT_amount = transaction.cart_VAT_amount

            is_guest = transaction.is_guest

            if transaction.payment_status == PAYMENT_STATUS_PAID:
                redirect_url = transaction.success_url

            if transaction.payment_status in self.list_failure_statuses:
                redirect_url = transaction.failure_url

            if transaction.payment_status == PAYMENT_STATUS_CANCELLED:
                redirect_url = transaction.cancel_url

            # add transaction id in response
            if redirect_url:
                redirect_url = (redirect_url + '?transaction_id=' +
                                str(transaction.transaction_id))
            sessionkey = self.get_browser_value(transaction)

        response_data = {
            "data": {
                "api_client": api_client,
                "payment_options": payment_options,
                "checkoutpg_config": checkoutpg_config,
                "adcb_config": adcb_config,
                "tabbypg_config": tabbypg_config,
                "applepay_config": applepay_config,
                "paypal_config": paypal_config,

                "amount": amount,
                "currency": currency,
                "country_code": country_code,
                "service_fee": service_fee,
                "vat_amount": VAT_amount,
                "base_amount": base_amount,

                "cart_amount": cart_amount,
                "cart_currency": cart_currency,
                "cart_service_fee": cart_service_fee,
                "cart_vat_amount": cart_VAT_amount,
                "cart_base_amount": cart_base_amount,

                "qitaf_config": qitaf_config,
                "citi_config": citi_config,

                "redirect_url": redirect_url,
                "announcements": announcements_dict,

                "is_guest": is_guest,
                "allow_aed_converted_amount": aed_amount_flag,
                "sessionkey": sessionkey
            },
        }

        return response_data

    def get_tabby_conf(self, payment_option):
        tabby_enabled = payment_option.get(PAYMENT_OPTION_TABBYPG, False)
        tabbypg_config = {}
        if tabby_enabled:
            tabbypg_obj = TabbyPGManager()
            tabbypg_obj = tabbypg_obj.tabbypg_config
            if tabbypg_obj:
                tabbypg_config[
                    "validation_json"] = tabbypg_obj.validation_json
        return tabbypg_config

    def get_additional_config(self, additional_fee, payment_type):
        """
        returns additional charge configured dict
        """
        additional_charges = False
        additional_percentage = 0
        additional_fixed_amount = 0
        if additional_fee:
            additional_charges = True
            additional_percentage = additional_fee.percentage
            additional_fixed_amount = additional_fee.fixed_amount
        return {"additional_charges": additional_charges,
                "payment_option": payment_type,
                "additional_percentage": additional_percentage,
                "additional_fixed_amount": additional_fixed_amount}

    def get_applepay_config(self, payment_option):
        """
        returns applepay additional fee config
        only if applepay is enabled
        """
        applepay_config = {}
        applepay_config["supportedNetworks"] = APPLEPAY_SUPPORTED_NETWORKS
        applepay_config[
            "merchantCapabilities"] = APPLEPAY_MERCHANT_CAPABILITIES
        applepay_config["label"] = APPLEPAY_LABEL

        applepay_enabled = payment_option.get(
            PAYMENT_OPTION_CHECKOUT_APPLEPAY, False)
        if applepay_enabled:
            additional_fee = get_gateway_additional_fee(TOKEN_TYPE_APPLEPAY)
            applepay_config.update(self.get_additional_config(additional_fee,
                                                              TOKEN_TYPE_APPLEPAY))
        return applepay_config

    def get_paypal_config(self, payment_option):
        """
        returns paypal process fee config
        only if paypal is enabled
        """
        paypal_config = {}
        paypal_enabled = payment_option.get(PAYMENT_OPTION_PAYPAL, False)
        if paypal_enabled:
            additional_fee = get_gateway_additional_fee(TOKEN_TYPE_PAYPAL)
            paypal_config = self.get_additional_config(additional_fee,
                                                       TOKEN_TYPE_PAYPAL)
        return paypal_config

    def get_qitaf_config(self, payment_option, transaction_data,
                         partial_redemption_allowed_options):
        """
        returns qitaf configurations
        """
        qitaf_enabled = payment_option.get(PAYMENT_OPTION_QITAF, False)
        if qitaf_enabled:
            partial_redemption_allowed = partial_redemption_allowed_options.get(
                PAYMENT_OPTION_QITAF, False)
            qitaf_obj = QitafServiceManager()
            qitaf_config = qitaf_obj.get_configurations(
                transaction_data.amount, transaction_data.currency,
                transaction_data.transaction_id)
            if qitaf_config:
                additional_config = {
                    'qitaf_phone_number': transaction_data.qitaf_phone_number,
                    'is_qitaf_enabled': transaction_data.is_qitaf_enabled,
                    'partial_redemption_allowed': partial_redemption_allowed
                }
                qitaf_config.update(additional_config)
            else:
                logger.error(
                    "Qitaf configuration not found for transaction id: "
                    "{}".format(transaction_data.transaction_id))
                qitaf_config = {}
            return qitaf_config
        else:
            return None

    def get_browser_value(self, transaction_obj):
        letters = string.ascii_lowercase
        if transaction_obj.browser_value:
            browser_value = transaction_obj.browser_value
            logger.info("subsequent returned browser value is "
                        "{}".format(browser_value))
            browser_value = encrypt_browser_value(browser_value)
        else:
            browser_value = ''.join(random.choice(letters) for i in range(15))
            try:
                browser_value_transaction = YouPayTransactionData.objects.get(
                    transaction_id=transaction_obj.transaction_id)
                browser_value_transaction.browser_value = browser_value
                browser_value_transaction.save()
                logger.info("first returned browser value is {}".format(
                    browser_value))
                browser_value = encrypt_browser_value(browser_value)
            except YouPayTransactionData.DoesNotExist:
                browser_value = None
        if browser_value:
            logger.info("returned encrypted browser value is {}".format(
                browser_value))
        return browser_value

    def check_citi_allowed_denominations(self, payment_option, transaction):
        """
        returns citi configurations
        """
        citi_config = {}
        citi_enabled = payment_option.get(PAYMENT_OPTION_CITI_REWARDS, False)
        if citi_enabled:
            base_value = transaction.base_amount
            citi_allowed = False
            if base_value % 100 == 0:
                citi_allowed = True
            if citi_allowed:
                citi_obj = CitiRewardsManager()
                cit_available_balance = citi_obj.get_citi_account_balance(
                    transaction)
                if cit_available_balance < base_value:
                    citi_allowed = False
            citi_config = {
                'citi_allowed': citi_allowed
            }
        return citi_config

    def get_checkout_config(self, payment_option, transaction):
        card__enabled = payment_option.get(PAYMENT_OPTION_CHECKOUT_CARD,
                                           False)
        saved_card__enabled = payment_option.get(
            PAYMENT_OPTION_CHECKOUT_SAVED_CARD,
            False)
        checkout_config = {}
        if True in [card__enabled, saved_card__enabled]:
            checkout_obj = CheckoutpgManager()
            checkout_config, status_code = (
                checkout_obj.get_configurations(transaction.currency)
            )

            logger.info(
                "checkoutpg response : {}, {}".format(checkout_config,
                                                      status_code))
        return checkout_config

    def get_adcb_config(self, payment_option, transaction,
                        partial_redemption_allowed_options):
        """
        This is for ADCB payback
        """
        adcb_enabled = payment_option.get(PAYMENT_OPTION_ADCB, False)
        partial_redemption_allowed = partial_redemption_allowed_options.get(
            PAYMENT_OPTION_ADCB, False)
        adcb_config = {}
        if adcb_enabled:
            b2c_payback_obj = B2CPaybackManager()
            adcb_config = b2c_payback_obj.get_configurations(
                transaction.amount, transaction.currency,
                transaction.transaction_id)
            if adcb_config:
                adcb_config[
                    'partial_redemption_allowed'] = partial_redemption_allowed
        return adcb_config

    def get_session_key(self, request):
        session_key = request.COOKIES.get('sessionkey')
        logger.info(
            "request cookies value is {}, cookie keys are {}, cookie session "
            "key is {}".format(
                request.COOKIES, request.COOKIES.keys(), session_key))
        if session_key == 'null':
            session_key = None
        else:
            session_key = decrypt_browser_value(session_key)
        return session_key

    def check_browser_session(self, transaction, session_key):
        logger.info("User session check browser value {}, session key {}"
                    "".format(transaction.browser_value, session_key))
        if transaction.browser_value:
            if transaction.browser_value == session_key:
                return True
            elif transaction.browser_value != session_key:
                return False
        else:
            return True



class ClientStaticFilesAPI(APIView):
    """
    Static files view
    """

    def get(self, request):
        """
        Get static files
        """
        response_obj = YouPayResponse()

        transaction_id = decrypt_string(request.GET.get('id', None))

        try:

            transaction_obj = YouPayTransactionData.objects.get(
                transaction_id=transaction_id)

            client = transaction_obj.api_client
            if client:
                api_client_data = {
                    'color': client.color_code,
                    'mobile_logo': get_mobile_logo_url(client),
                    'logo': get_logo_url(client)
                }

                data = response_obj.get_success_dict(
                    code=response_obj.SUCCESS,
                    success_dict=api_client_data
                )

                return Response(data, status=status.HTTP_200_OK)
            else:
                logger.error("Client not found for transaction id : {}"
                             "".format(transaction_id))

                data = response_obj.get_error_dict(
                    error_code=response_obj.MISSING_CLIENT_INFO)
                return Response(data.get('errors'),
                                status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            message = str(e)
            logger.error("Exception occurred while retrieving static files "
                         "for transaction {} : {}  ".format(transaction_id,
                                                            message))
            data = response_obj.get_404_message(message=str(e))
            return Response(
                data,
                status=status.HTTP_404_NOT_FOUND)


def get_logo_url(client):
    if client.logo_file and hasattr(client.logo_file, 'url'):
        return client.logo_file.url
    else:
        return None


def get_mobile_logo_url(client):
    if client.mobile_logo_file and hasattr(client.mobile_logo_file,
                                           'url'):
        return client.mobile_logo_file.url
    else:
        return None
