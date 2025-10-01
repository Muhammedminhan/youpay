import logging
import random
import string

from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

from core.exceptions import PaymentConfigurationFailed
from core.models import PaymentMethodConfig, Country
from core.response_messages import YouPayResponse
from core.utils import (decrypt_string, get_gateway_additional_fee,
                        get_configuration_data, encrypt_browser_value,
                        decrypt_browser_value, get_display_platform,
                        get_display_program)
from integrations.constants import (ADCB_CLIENT_CODE, CHECKOUTPG_HUB_CODE,
                                    QITAF_CLIENT_CODE,
                                    NEQATY_CLIENT_CODE, MOKAFAA_CLIENT_CODE,
                                    ANB_CLIENT_CODE,
                                    ADDITIONAL_PROCESSING_FEE,
                                    PAYPAL_HUB_CODE)
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
    PAYMENT_OPTION_ADCB, PAYMENT_OPTION_NEQATY, PAYMENT_OPTION_MOKAFA,
    EXPIRED_STATUS_LIST, PAYMENT_OPTION_ANB, PAYMENT_METHOD_PAYPAL
)
from payments.models import YouPayTransactionData
from services.constants import (TOKEN_TYPE_PAYPAL, TOKEN_TYPE_APPLEPAY,
                                APPLEPAY_SUPPORTED_NETWORKS,
                                APPLEPAY_MERCHANT_CAPABILITIES,
                                APPLEPAY_LABEL)
from services.v1.serializers.client_registrattion import (
    PaymentGatewaySerializer
)
from services.v1.views.common import ClientValidator
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
        self.list_expired_statuses = EXPIRED_STATUS_LIST

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
            if not decrypted_transaction_id:
                error_message = (
                    "Invalid payment, configuration not found for "
                    "{}").format(pk)
                logger.info(error_message)
                raise PaymentConfigurationFailed(error_message)
            transaction = YouPayTransactionData.objects.get(
                transaction_id=decrypted_transaction_id)
            # session_key = self.get_session_key(request)
            if not transaction:
                return self._transaction_not_found_response()

            if transaction.payment_status in self.list_end_statuses:
                return self._transaction_already_processed_response(
                    transaction)

            if not transaction.api_client.validate_session:
                session_id = transaction.session_id

            country = get_country_for_configuration(transaction)
            if not country:
                return self._country_not_available_response()
            country_name = country.name

            client = get_client_for_configuration(transaction)
            if not client:
                return self._client_not_found_response()

            payment_options, payment_config_data = (
                get_payment_methods(transaction, client, country))

            if transaction.session_id != session_id:
                return self._session_expired_response()

            response_data = self.retrieve_response(
                transaction=transaction,
                payment_options=payment_options,
                payment_config_data=payment_config_data,
                client=client,
                country_name=country_name
            )

            return Response(self.response_obj.get_success_dict(
                code=self.response_obj.SUCCESS, success_dict=response_data),
                status=status.HTTP_200_OK)

        except Exception as e:
            return self._exception_response(e)

    def retrieve_response(self, **kwargs):
        transaction = kwargs.get('transaction')
        payment_options = kwargs.get('payment_options')
        payment_config_data = kwargs.get(
            'payment_config_data')
        country_name = kwargs.get('country_name')
        client = kwargs.get('client')
        api_client = {
            'color': client.color_code,
            'mobile_logo': get_mobile_logo_url(client),
            'logo': get_logo_url(client)
        }

        response_data = {
            "data": {
                "api_client": api_client,
                "payment_options": payment_options,
                "amount": transaction.amount if transaction else None,
                "currency": transaction.currency if transaction else None,
                "country_code": transaction.country_code if transaction else
                None,
                "service_fee": transaction.service_fee if transaction else
                None,
                "paypal_config": self.get_paypal_config(payment_options,
                                                        transaction),
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
                "redirect_url": self._get_redirect_url(transaction),
                "announcements": get_announcements(transaction.platform),
                "is_guest": transaction.is_guest,
                "allow_aed_converted_amount":
                    transaction.api_client.allow_aed_converted_amount,
                "program": get_display_program(transaction.api_client),
                "platform": get_display_platform(transaction.platform),
                "retry_count": transaction.retry_count,
                "store": country_name,
                "customer_email": transaction.customer_email,
                "client_code": client.client_code,
                "is_offer_enabled": transaction.is_offer_applicable,
                "purchase_origin": (transaction.clevertap_items or {}).get(
                    "purchase_origin"),
                **payment_config_data,
            }
        }

        return response_data

    def _transaction_not_found_response(self):
        data = self.response_obj.get_error_dict(
            error_code=self.response_obj.UNKNOWN_ERR)
        return Response(data.get('errors'), status=status.HTTP_404_NOT_FOUND)

    def _transaction_already_processed_response(self, transaction):
        response_data = self.response_obj.get_success_dict(
            code=self.response_obj.TRANSACTION_ALREADY_CLOSED)
        redirect_url = self._get_redirect_url(transaction)
        complete_url = None
        if redirect_url:
            complete_url = (redirect_url + '?transaction_id=' +
                            str(transaction.transaction_id))
        response_data["redirect_url"] = complete_url
        data = {
            "data": response_data
        }
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
        logger.error(
            "Error occurred during configuration api call, {}".format(e),
            exc_info=e)
        data = self.response_obj.get_404_message(message=str(e))
        return Response(data, status=status.HTTP_404_NOT_FOUND)

    def _get_redirect_url(self, transaction):
        if transaction.payment_status == PAYMENT_STATUS_PAID:
            return transaction.success_url
        elif transaction.payment_status == PAYMENT_STATUS_CANCELLED:
            return transaction.cancel_url
        elif transaction.payment_status in self.list_end_statuses:
            return transaction.failure_url
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

    def get_applepay_config(self, payment_option, transaction):
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
            additional_fee = None
            additional_config = self.get_additional_config(additional_fee,
                                                           TOKEN_TYPE_APPLEPAY)
            applepay_config.update(additional_config)
        return applepay_config

    def get_paypal_config(self, payment_option, transaction):
        paypal_config = {}
        currency = transaction.cart_currency
        charge_type = ADDITIONAL_PROCESSING_FEE
        payment_gateway = PAYPAL_HUB_CODE
        payment_method = PAYMENT_METHOD_PAYPAL
        paypal_enabled = payment_option.get(PAYMENT_OPTION_PAYPAL, False)

        if paypal_enabled:
            additional_fee = get_gateway_additional_fee(currency, charge_type,
                                                        payment_gateway,
                                                        payment_method)
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
                                                     transaction)

        return checkout_config

    def get_b2c_config(self, payment_option, transaction,
                       payment_config_data):
        adcb_enabled = payment_option.get(PAYMENT_OPTION_ADCB, False)
        qitaf_enabled = payment_option.get(PAYMENT_OPTION_QITAF, False)
        neqaty_enabled = payment_option.get(PAYMENT_OPTION_NEQATY, False)
        mokafa_enabled = payment_option.get(PAYMENT_OPTION_MOKAFA, False)
        anb_enabled = payment_option.get(PAYMENT_OPTION_ANB, False)
        config_dict = {}
        if True in [adcb_enabled, qitaf_enabled, neqaty_enabled,
                    mokafa_enabled, anb_enabled]:
            b2c_config = {}
            config_list = (b2c_config.response_data.get("results") if
                           b2c_config else {})
            if adcb_enabled:
                adcb_config = self.get_each_b2c_config(config_list,
                                                       ADCB_CLIENT_CODE)
                this__config_data = (
                    payment_config_data.get(
                        PAYMENT_OPTION_ADCB, {}))
                adcb_config.update(**this__config_data)
                config_dict['adcb_config'] = adcb_config

            if qitaf_enabled:
                this__config_data = (
                    payment_config_data.get(
                        PAYMENT_OPTION_QITAF, {}))
                qitaf_config = self.get_each_b2c_config(config_list,
                                                        QITAF_CLIENT_CODE)
                additional_config = {
                    'qitaf_phone_number': transaction.qitaf_phone_number,
                    'is_qitaf_enabled': transaction.is_qitaf_enabled,
                    **this__config_data
                }
                qitaf_config.update(additional_config)
                config_dict['qitaf_config'] = qitaf_config

            if neqaty_enabled:
                this__config_data = (
                    payment_config_data.get(
                        PAYMENT_OPTION_NEQATY, {}))
                neqaty_config = self.get_each_b2c_config(config_list,
                                                         NEQATY_CLIENT_CODE)
                neqaty_config.update(**this__config_data)
                config_dict['neqaty_config'] = neqaty_config

            if mokafa_enabled:
                this__config_data = (
                    payment_config_data.get(
                        PAYMENT_OPTION_MOKAFA, {}))
                mokafa_config = self.get_each_b2c_config(config_list,
                                                         MOKAFAA_CLIENT_CODE)
                mokafa_config.update(**this__config_data)
                config_dict['mokafa_config'] = mokafa_config

            if anb_enabled:
                this__config_data = (
                    payment_config_data.get(
                        PAYMENT_OPTION_ANB, {}))
                anb_config = self.get_each_b2c_config(config_list,
                                                      ANB_CLIENT_CODE)
                anb_config.update(**this__config_data)
                config_dict['anb_config'] = anb_config
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
                    'logo': get_logo_url(client),
                    "program": get_display_program(client),
                    "client_code": client.client_code,
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


class RedemptionPartnerPrograms(APIView, ClientValidator, YouPayResponse):
    """
    API view for retrieving redemption partner programs for a client.
    """

    def get(self, request):
        """
        Handles GET requests to retrieve redemption partner programs.

        Args:
            request: The HTTP request object.

        Returns:
            Response: DRF Response object with payment options and configuration map.
        """
        validate, client = self.validate_client(request)
        if not validate:
            logger.info(
                "Payment request client validation failed for order_reference"
            )
            self.return_data = self.get_400_message(
                message="Client Does Not Exist"
            )
            return Response(
                self.return_data.get('errors'),
                status=status.HTTP_400_BAD_REQUEST
            )
        country_code = request.GET.get('country_code', None)
        country = Country.objects.get(iso_code=country_code)
        language_code = request.GET.get('lang', None)

        try:
            is_guest = True if request.GET.get(
                'is_guest').lower() == 'true' else False
            payment_method_query = Q(
                payment_method__active=True,
                client=client,
                active=True,
                payment_method__burn_full_redemption_enabled=True,
                country=country
            )
            if is_guest:
                payment_method_query &= Q(guest_user_enabled=True)
            payment_method_configs = PaymentMethodConfig.objects.filter(
                payment_method_query
            )

            payment_options = []

            for config in payment_method_configs:
                method = config.payment_method
                method_key = method.payment_method
                try:
                    if method.is_second_project_config_enabled:
                        method_specific_config = method.payment_method_config

                        if method_specific_config:
                            payment_options.append({
                                "name": method_key,
                                "display_name": method_specific_config.get(
                                    'display_name_ar') if language_code == 'ar' else method_key,
                                "code": method_specific_config.get("code"),
                                "logo": method_specific_config.get("logo"),
                                "redemption_amount": method_specific_config.get(
                                    "redemption_amount")
                            })
                        else:
                            logger.error(
                                "Missing second project configuration for method=%s",
                                method.code
                            )
                            continue
                except Exception as inner_exc:
                    logger.error(
                        "Error while processing payment method=%s: %s",
                        method_key,
                        str(inner_exc),
                        exc_info=True
                    )
                    continue

            response_data = {
                "payment_options": payment_options,
            }
            return Response(
                self.get_success_dict(
                    code=self.SUCCESS,
                    success_dict=response_data
                ),
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(
                "Error occurred while getting payment options: %s",
                str(e),
                exc_info=True
            )
            return Response(
                self.get_404_message(message=str(e)),
                status=status.HTTP_404_NOT_FOUND
            )
