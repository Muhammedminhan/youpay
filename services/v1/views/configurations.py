import logging
import random
import string

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

from core.response_messages import YouPayResponse
from core.utils import (decrypt_string, get_gateway_additional_fee,
                        get_configuration_data, encrypt_browser_value,
                        decrypt_browser_value)
from integrations.constants import (ADCB_CLIENT_CODE, B2CPAYBACK_HUB_CODE,
                                    CHECKOUTPG_HUB_CODE, QITAF_CLIENT_CODE,
                                    NEQATY_CLIENT_CODE)
from integrations.models import PaymentGateway
from integrations.v1.gateway_clients.citi_service import CitiRewardsManager
from integrations.v1.gateway_clients.tabbypg import TabbyPGManager
from payments.constants import (
    PAYMENT_STATUS_CANCELLED,
    PAYMENT_STATUS_PAID, PAYMENT_END_STATUS_LIST,
    PAYMENT_OPTION_CHECKOUT_APPLEPAY,
    PAYMENT_OPTION_PAYPAL, PAYMENT_OPTION_CITI_REWARDS, PAYMENT_OPTION_QITAF,
    PAYMENT_OPTION_TABBYPG, PAYMENT_OPTION_CHECKOUT_CARD,
    PAYMENT_OPTION_CHECKOUT_SAVED_CARD,
    PAYMENT_OPTION_ADCB, PAYMENT_OPTION_NEQATY
)
from payments.models import YouPayTransactionData
from services.constants import (TOKEN_TYPE_PAYPAL, TOKEN_TYPE_APPLEPAY,
                                APPLEPAY_SUPPORTED_NETWORKS,
                                APPLEPAY_MERCHANT_CAPABILITIES,
                                APPLEPAY_LABEL)
from services.v1.serializers.client_registrattion import (
    PaymentGatewaySerializer
)
from services.v1.views.utils import (get_announcements,
                                     get_session_id_from_header,
                                     get_country_for_configuration,
                                     get_client_for_configuration,
                                     get_payment_methods
                                     )

logger = logging.getLogger(__name__)


class ConfigViewSet(ViewSet):
    """
    Config viewset for getting payment gateways with transaction id
    """
    response_obj = YouPayResponse()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.list_end_statuses = PAYMENT_END_STATUS_LIST

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
            # session_key = self.get_session_key(request)
            if not transaction:
                return self._transaction_not_found_response()

            if transaction.payment_status in self.list_end_statuses:
                return self._transaction_already_paid_response(transaction)

            if not transaction.api_client.validate_session:
                session_id = transaction.session_id

            country = get_country_for_configuration(transaction)
            if not country:
                return self._country_not_available_response()

            client = get_client_for_configuration(transaction)
            if not client:
                return self._client_not_found_response()

            payment_options, partial_redemption_allowed_options = (
                get_payment_methods(transaction, client, country))

            if transaction.session_id != session_id:
                return self._session_expired_response()

            response_data = self.retrieve_response(
                transaction=transaction,
                payment_options=payment_options,
                partial_redemption_allowed_options=
                partial_redemption_allowed_options,
                client=client
            )

            return Response(self.response_obj.get_success_dict(
                code=self.response_obj.SUCCESS, success_dict=response_data),
                status=status.HTTP_200_OK)

        except Exception as e:
            return self._exception_response(e)

    def retrieve_response(self, **kwargs):
        transaction = kwargs.get('transaction')
        payment_options = kwargs.get('payment_options')
        partial_redemption_allowed_options = kwargs.get(
            'partial_redemption_allowed_options')
        client = kwargs.get('client')

        api_client = {
            'color': client.color_code,
            'mobile_logo': get_mobile_logo_url(client),
            'logo': get_logo_url(client)
        }

        checkoutpg_config = self.get_checkout_config(payment_options,
                                                     transaction)
        tabbypg_config = self.get_tabby_conf(payment_options)
        # sessionkey = self.get_browser_value(transaction) if transaction else None
        b2c_configs = self.get_b2c_config(payment_options,
                                          transaction,
                                          partial_redemption_allowed_options)
            
        response_data = {
            "data": {
                "api_client": api_client,
                "payment_options": payment_options,
                "checkoutpg_config": checkoutpg_config.response_data if
                checkoutpg_config else None,
                "adcb_config": b2c_configs.get('adcb_config', {}),
                "tabbypg_config": tabbypg_config,
                "applepay_config": self.get_applepay_config(payment_options),
                "paypal_config": self.get_paypal_config(payment_options),
                "neqaty_config": b2c_configs.get('neqaty_config', {}),
                "amount": transaction.amount if transaction else None,
                "currency": transaction.currency if transaction else None,
                "country_code": transaction.country_code if transaction else
                None,
                "service_fee": transaction.service_fee if transaction else
                None,
                "vat_amount": transaction.VAT_amount if transaction else None,
                "base_amount": transaction.base_amount if transaction else
                None,
                "cart_amount": transaction.cart_amount if transaction else
                None,
                "cart_currency": transaction.cart_currency if transaction else
                None,
                "cart_service_fee": transaction.cart_service_fee if
                transaction else None,
                "cart_vat_amount": transaction.cart_VAT_amount if transaction
                else None,
                "cart_base_amount": transaction.cart_base_amount if
                transaction else None,
                "qitaf_config": b2c_configs.get('qitaf_config', {}),
                "citi_config": self.check_citi_allowed_denominations(
                    payment_options, transaction),
                "redirect_url": self._get_redirect_url(transaction),
                "announcements": get_announcements(transaction.platform),
                "is_guest": transaction.is_guest,
                "allow_aed_converted_amount":
                    transaction.api_client.allow_aed_converted_amount,
                "program": transaction.api_client.name,
                "platform": transaction.platform
            },
        }

        return response_data

    def _transaction_not_found_response(self):
        data = self.response_obj.get_error_dict(
            error_code=self.response_obj.UNKNOWN_ERR)
        return Response(data.get('errors'), status=status.HTTP_404_NOT_FOUND)

    def _transaction_already_paid_response(self, transaction):
        return_response = self.retrieve_response(
            payment_options=None,
            checkoutpg_config=None,
            transaction=transaction,
            announcements_dict=None,
            status_code=None
        )
        data = self.response_obj.get_success_dict(
            code=self.response_obj.SUCCESS, success_dict=return_response)
        return Response(data, status=status.HTTP_200_OK)

    def _country_not_available_response(self):
        message = "Not available for this country"
        data = self.response_obj.get_404_message(message=message)
        return Response(data, status=status.HTTP_404_NOT_FOUND)

    def _client_not_found_response(self):
        message = "Client doesn't exist"
        data = self.response_obj.get_404_message(message=message)
        return Response(data, status=status.HTTP_404_NOT_FOUND)

    def _session_expired_response(self):
        message = "Session expired or doesn't match"
        data = self.response_obj.get_404_message(message=message)
        return Response(data, status=status.HTTP_404_NOT_FOUND)

    def _exception_response(self, e):
        data = self.response_obj.get_404_message(message=str(e))
        return Response(data, status=status.HTTP_404_NOT_FOUND)

    def _get_redirect_url(self, transaction):
        if transaction.payment_status == PAYMENT_STATUS_PAID:
            return transaction.success_url
        elif transaction.payment_status in self.list_end_statuses:
            return transaction.failure_url
        elif transaction.payment_status == PAYMENT_STATUS_CANCELLED:
            return transaction.cancel_url
        else:
            return None

    @staticmethod
    def get_tabby_conf(payment_option):
        tabby_enabled = payment_option.get(PAYMENT_OPTION_TABBYPG, False)
        tabbypg_config = {}

        if tabby_enabled:
            tabbypg_obj = TabbyPGManager()
            tabbypg_obj = tabbypg_obj.tabbypg_config

            if tabbypg_obj:
                tabbypg_config['validation_json'] = tabbypg_obj.validation_json

        return tabbypg_config

    @staticmethod
    def get_additional_config(additional_fee, payment_type):
        if additional_fee:
            return {
                "additional_charges": True,
                "payment_option": payment_type,
                "additional_percentage": additional_fee.percentage,
                "additional_fixed_amount": additional_fee.fixed_amount
            }
        else:
            return {
                "additional_charges": False,
                "payment_option": payment_type,
                "additional_percentage": 0,
                "additional_fixed_amount": 0
            }

    def get_applepay_config(self, payment_option):
        """
        returns applepay additional fee config
        only if applepay is enabled
        """
        applepay_config = {"supportedNetworks": APPLEPAY_SUPPORTED_NETWORKS,
                           "merchantCapabilities":
                               APPLEPAY_MERCHANT_CAPABILITIES,
                           "label": APPLEPAY_LABEL}
        applepay_enabled = payment_option.get(PAYMENT_OPTION_CHECKOUT_APPLEPAY,
                                              False)

        if applepay_enabled:
            additional_fee = get_gateway_additional_fee(TOKEN_TYPE_APPLEPAY)
            additional_config = self.get_additional_config(additional_fee,
                                                           TOKEN_TYPE_APPLEPAY)
            applepay_config.update(additional_config)
        return applepay_config

    def get_paypal_config(self, payment_option):
        paypal_config = {}
        paypal_enabled = payment_option.get(PAYMENT_OPTION_PAYPAL, False)

        if paypal_enabled:
            additional_fee = get_gateway_additional_fee(TOKEN_TYPE_PAYPAL)
            paypal_config = self.get_additional_config(additional_fee,
                                                       TOKEN_TYPE_PAYPAL)

        return paypal_config

    @staticmethod
    def get_browser_value(transaction_obj):
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

    @staticmethod
    def check_citi_allowed_denominations(payment_option, transaction):
        citi_config = {}
        citi_enabled = payment_option.get(PAYMENT_OPTION_CITI_REWARDS, False)

        if citi_enabled and transaction.base_amount % 100 == 0:
            citi_obj = CitiRewardsManager()
            cit_available_balance = citi_obj.get_citi_account_balance(
                transaction)

            if cit_available_balance >= transaction.base_amount:
                citi_config['citi_allowed'] = True

        return citi_config

    @staticmethod
    def get_checkout_config(payment_option, transaction):
        card_enabled = payment_option.get(PAYMENT_OPTION_CHECKOUT_CARD, False)
        saved_card_enabled = payment_option.get(
            PAYMENT_OPTION_CHECKOUT_SAVED_CARD, False)
        checkout_config = {}

        if True in [card_enabled, saved_card_enabled]:
            checkout_config = get_configuration_data(CHECKOUTPG_HUB_CODE,
                                                     transaction.currency)

        return checkout_config

    def get_b2c_config(self, payment_option, transaction,
                       partial_redemption_allowed_options):
        adcb_enabled = payment_option.get(PAYMENT_OPTION_ADCB, False)
        qitaf_enabled = payment_option.get(PAYMENT_OPTION_QITAF, False)
        neqaty_enabled = payment_option.get(PAYMENT_OPTION_NEQATY, False)
        config_dict = {}
        if True in [adcb_enabled, qitaf_enabled, neqaty_enabled]:
            b2c_config = get_configuration_data(B2CPAYBACK_HUB_CODE,
                                                transaction.currency)
            config_list = (b2c_config.response_data.get("results") if
                           b2c_config else {})
            if adcb_enabled:
                adcb_config = self.get_each_b2c_config(config_list,
                                                       ADCB_CLIENT_CODE)
                partial_redemption_allowed = (
                    partial_redemption_allowed_options.get(
                        PAYMENT_OPTION_ADCB, False))
                adcb_config[
                    'partial_redemption_allowed'] = partial_redemption_allowed
                config_dict['adcb_config'] = adcb_config

            if qitaf_enabled:
                partial_redemption_allowed = (
                    partial_redemption_allowed_options.get(
                        PAYMENT_OPTION_QITAF, False))
                qitaf_config = self.get_each_b2c_config(config_list,
                                                        QITAF_CLIENT_CODE)
                additional_config = {
                    'qitaf_phone_number': transaction.qitaf_phone_number,
                    'is_qitaf_enabled': transaction.is_qitaf_enabled,
                    'partial_redemption_allowed': partial_redemption_allowed
                }
                qitaf_config.update(additional_config)
                config_dict['qitaf_config'] = qitaf_config

            if neqaty_enabled:
                partial_redemption_allowed = (
                    partial_redemption_allowed_options.get(
                        PAYMENT_OPTION_QITAF, False))
                neqaty_config = self.get_each_b2c_config(config_list,
                                                         NEQATY_CLIENT_CODE)
                additional_config = {
                    'partial_redemption_allowed': partial_redemption_allowed
                }
                neqaty_config.update(additional_config)
                config_dict['neqaty_config'] = neqaty_config
        return config_dict

    @staticmethod
    def get_each_b2c_config(config_list, payment_method_code):
        for config in config_list:
            if config["code"] == payment_method_code:
                return config
        return {}

    @staticmethod
    def get_session_key(request):
        session_key = request.COOKIES.get('sessionkey')
        logger.info(
            "request cookies value is {}, cookie keys are {}, cookie session "
            "key is {}".format(
                request.COOKIES, request.COOKIES.keys(), session_key))
        try:
            if session_key in ['null', 'undefined', None, 'None', 'none']:
                session_key = None
            else:
                session_key = decrypt_browser_value(session_key)
        except Exception as e:
            logger.error("Error occurred during resolving session key",
                         exc_info=e)
            session_key = None
        return session_key

    @staticmethod
    def check_browser_session(transaction, session_key):
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
