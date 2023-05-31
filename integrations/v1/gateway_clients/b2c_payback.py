import json
import logging

import requests
from rest_framework import status

from core.constants import REQUEST_METHOD_POST, REQUEST_METHOD_GET
from core.messages import IS_SUCCESS, REDIRECT_URL, IS_REDIRECT
from core.utils import (get_payment_gateway_config,
                        decrypt_string
                        )
from integrations.constants import (ADCB_POINT_BALANCE_API,
                                    B2CPAYBACK_HUB_CODE, B2CP_CACHE_KEY,
                                    ADCB_AUTHENTICATE_API,
                                    ADCB_REDEMPTION_API, ADCB_HEADERS,
                                    ADCB_VERIFY_API,
                                    PAYMENT_REQUEST_POINT_BALANCE,
                                    PAYMENT_REQUEST_AUTHENTICATE,
                                    PAYMENT_REQUEST_REDEMPTION,
                                    PAYMENT_REQUEST_VERIFY,
                                    CHECKOUT_UAE_CURRENCY)
from integrations.v1.gateway_clients.utils import (
    format_adcb_redemption_data,
    format_adcb_verify_data,
    get_adcb_verify_redirect_url,
    get_adcb_redemption_redirect_url
)
from integrations.v1.serializers.b2c_payback_payment_request import (
    PointBalanceRequestSerializer,
    AuthenticateRequestSerializer
)
from payments.constants import (PAYMENT_STATUS_DECLINED_RETRY,
                                PAYMENT_STATUS_PAID, PAYMENT_STATUS_FAILED)
from payments.serializers.youpay_payments import (
    YouPayTransactionDataSerializer
)
from services.v1.constants import (B2C_PAYBACK_YOUPAY_PRODUCT_CODE,
                                   B2C_PAYBACK_CONFIG_ENDPOINT
                                   )
from services.v1.views.payment import PaymentRequestView
from services.v1.views.payment_handlers import PaymentHandlers

logger = logging.getLogger(__name__)


class B2CPaybackManager(PaymentHandlers, PaymentRequestView):
    """
    Class to manage b2cpayback related operations
    """

    def get_configurations(self, amount, currency, transaction_id):
        product_code = B2C_PAYBACK_YOUPAY_PRODUCT_CODE
        amount = str(amount)
        currency = str(currency)
        if currency != CHECKOUT_UAE_CURRENCY:
            logger.info(
                "Skipping config api call to b2cpayback for non AED "
                "transaction {}".format(transaction_id))
            return None
        else:
            config_request_data = {
                "amount": amount, "currency": currency,
                "product_code": product_code
            }
            request_data_json = json.dumps(config_request_data)
            b2c_gateway_obj = get_payment_gateway_config(B2CP_CACHE_KEY,
                                                         B2CPAYBACK_HUB_CODE)
            b2c_payback_domain = b2c_gateway_obj.domain
            try:
                url = b2c_payback_domain + B2C_PAYBACK_CONFIG_ENDPOINT

                response = requests.post(url, data=request_data_json,
                                         headers=ADCB_HEADERS)
                if response:
                    return response.json()
                else:
                    logger.error(
                        "No configuration received from configuration api "
                        "call to b2cpayback for transaction {}, response "
                        "{}".format(transaction_id, response.text))
                    return None
            except Exception as e:
                logger.error("config api call to b2cpayback failed",
                             exc_info=e)
                return None

    def get_point_balance(self, request_data):
        request_transaction_id = request_data.get('transaction_id')
        if request_transaction_id:
            try:
                transaction_obj = self.get_youpay_transaction_data(
                    decrypt_string(request_transaction_id))
                transaction_data = YouPayTransactionDataSerializer(
                    transaction_obj)
                request_dict = {
                    'data': request_data,
                    'transaction_data': transaction_data.data
                }
                verify_response, verify_status = self.verify_transaction(
                    transaction_data.data)
                logger.info(
                    "Verify response: {} - {}".format(verify_status,
                                                      verify_response))

                is_verified = verify_response.get('is_verified', False)
                if verify_status == status.HTTP_200_OK and is_verified:
                    balance_request_data = PointBalanceRequestSerializer(
                        request_dict)
                    request_data_json = json.dumps(balance_request_data.data)
                    b2c_gateway_obj = get_payment_gateway_config(
                        B2CP_CACHE_KEY, B2CPAYBACK_HUB_CODE)
                    b2c_payback_domain = b2c_gateway_obj.domain
                    ADCB_HEADERS['X-API-KEY'] = b2c_gateway_obj.api_key
                    url = b2c_payback_domain + ADCB_POINT_BALANCE_API
                    response = requests.post(url, data=request_data_json,
                                             headers=ADCB_HEADERS)
                    self.create_youpay_to_payment_gateways_data(
                        transaction_obj=transaction_obj,
                        transaction_id=transaction_obj.transaction_id,
                        request_data=request_data_json,
                        response_data=response.text,
                        request_method=REQUEST_METHOD_POST,
                        request_type=PAYMENT_REQUEST_POINT_BALANCE
                    )
                    if response:
                        return response, transaction_obj.transaction_id, None
                    else:
                        logger.error(
                            "Error response received from point balance api "
                            "call to b2cpayback for transaction {0}, {1}"
                            "".format(transaction_obj.transaction_id,
                                      response.text))
                        return response, None, None
                else:
                    msg = (
                        "Youpay b2c transaction verification failed for "
                        "transaction id {} response is : {} ".format(
                            transaction_obj.transaction_id, verify_response))
                    logger.error(msg)
                    return (verify_response, None,
                            self.CLIENT_TRANSACTION_VERIFICATION_FAILED)

            except Exception as e:
                logger.error(
                    "point balance api call to b2cpayback failed for "
                    "transaction {}".format(
                        request_transaction_id), exc_info=e)
                return None, None, None
        else:
            logger.error("Invalid transaction id received for point balance "
                         "api")
            return None, None, None

    def authenticate_redemption(self, request_data):
        request_transaction_id = request_data.get('transaction_id')
        try:
            transaction_obj = self.get_youpay_transaction_data(
                decrypt_string(request_transaction_id))
            transaction_data = YouPayTransactionDataSerializer(
                transaction_obj)

            request_dict = {
                'data': request_data,
                'transaction_data': transaction_data.data
            }
            authenticate_request_data = AuthenticateRequestSerializer(
                request_dict)
            update_data = {
                'cko-card-token': request_data.get('cko-card-token')}
            update_data.update(authenticate_request_data.data)
            request_data_json = json.dumps(update_data)
            b2c_gateway_obj = get_payment_gateway_config(
                B2CP_CACHE_KEY,
                B2CPAYBACK_HUB_CODE)
            b2c_payback_domain = b2c_gateway_obj.domain
            url = b2c_payback_domain + ADCB_AUTHENTICATE_API
            response = requests.post(url, data=request_data_json,
                                     headers=ADCB_HEADERS)
            self.create_youpay_to_payment_gateways_data(
                transaction_obj=transaction_obj,
                transaction_id=transaction_obj.transaction_id,
                request_data=request_data_json,
                response_data=response.text,
                request_method=REQUEST_METHOD_POST,
                request_type=PAYMENT_REQUEST_AUTHENTICATE
            )
            if response:
                if response.json().get('url'):
                    response_data = response.json()
                    response_data['is_redirect'] = True
                    return response_data, transaction_obj
                else:
                    return response.json(), transaction_obj
            else:
                logger.error(
                    "Error response received from authenticate api call "
                    "to b2cpayback for transaction {0}, {1}".format(
                        transaction_obj.transaction_id,
                        response.text))
                return response, None

        except Exception as e:
            logger.error(
                "authenticate api call to b2cpayback failed for "
                "transaction {}".format(
                    decrypt_string(request_transaction_id)), exc_info=e)
            return None, None

    def point_redemption(self, request_data):
        request_transaction_id = request_data.get('transaction_id')
        if request_transaction_id:
            try:
                transaction_obj = self.get_youpay_transaction_data(
                    decrypt_string(request_transaction_id))
                formatted_data = format_adcb_redemption_data(
                    request_data, transaction_obj
                )
                request_data_json = json.dumps(formatted_data)
                b2c_gateway_obj = get_payment_gateway_config(
                    B2CP_CACHE_KEY, B2CPAYBACK_HUB_CODE)
                b2c_payback_domain = b2c_gateway_obj.domain
                url = b2c_payback_domain + ADCB_REDEMPTION_API
                response = requests.post(url, data=request_data_json,
                                         headers=ADCB_HEADERS)
                self.create_youpay_to_payment_gateways_data(
                    transaction_obj=transaction_obj,
                    transaction_id=transaction_obj.transaction_id,
                    request_data=request_data_json,
                    response_data=response.text,
                    request_method=REQUEST_METHOD_POST,
                    request_type=PAYMENT_REQUEST_REDEMPTION
                )
                if response:
                    response_data = response.json()
                    response_data[IS_REDIRECT] = True
                    response_data[IS_SUCCESS] = True
                    response_data[REDIRECT_URL], transaction_status = (
                        get_adcb_redemption_redirect_url(response_data,
                                                         transaction_obj))
                    return response_data, transaction_obj
                else:
                    logger.error(
                        "Error response received from redemption api call "
                        "to b2cpayback {}".format(response.text))
                    return response, None
            except Exception as e:
                logger.error(
                    "redemption api call to b2cpayback failed", exc_info=e)
                return None, None
        else:
            logger.error("Invalid transaction id received for b2cpayback "
                         "redemption api")
            return None, None

    def verification(self, request_data):
        request_transaction_id = request_data.get('transaction_id')
        if request_transaction_id:
            try:
                transaction_obj = self.get_youpay_transaction_data(
                    decrypt_string(request_transaction_id))
                formatted_data = format_adcb_verify_data(
                    request_data, transaction_obj)
                b2c_gateway_obj = get_payment_gateway_config(
                    B2CP_CACHE_KEY, B2CPAYBACK_HUB_CODE)
                b2c_payback_domain = b2c_gateway_obj.domain
                url = b2c_payback_domain + ADCB_VERIFY_API
                formatted_data.pop("transaction_id")
                response = requests.get(url, params=formatted_data,
                                        headers=ADCB_HEADERS)
                response_data = response.json()
                response_data["is_redirect"] = True
                response_data[
                    "redirect_url"], transaction_status = (
                    get_adcb_verify_redirect_url(
                        response_data, transaction_obj))
                is_payment_verified = True
                approved_status = transaction_obj.approved
                if transaction_status:  # success case
                    payment_status = PAYMENT_STATUS_PAID
                    approved_status = True
                elif response_data.get(
                        "redirect_url") is None:  # checkoutpg declined
                    payment_status = PAYMENT_STATUS_DECLINED_RETRY
                    response_data[IS_SUCCESS] = False
                    is_payment_verified = False

                else:  # failure
                    payment_status = PAYMENT_STATUS_FAILED
                    approved_status = False
                    response_data[IS_SUCCESS] = False

                logger.info("adcb verify api call response : {}"
                            "".format(response_data))
                self.create_youpay_to_payment_gateways_data(
                    transaction_obj=transaction_obj,
                    transaction_id=transaction_obj.transaction_id,
                    request_data=json.dumps(formatted_data),
                    response_data=response.text,
                    request_method=REQUEST_METHOD_GET,
                    request_type=PAYMENT_REQUEST_VERIFY
                )
                if response_data:
                    update_data = {
                        'transaction_id': transaction_obj.transaction_id,
                        'payment_status': payment_status,
                        'payment_reference': (
                            response_data.get('payment_reference')
                            if response_data.get('payment_reference')
                            else response_data.get(
                                'results', {}).get('reference_id')),
                        'is_flagged': response_data.get('is_flagged', False),
                        'approved': approved_status,
                        'redeemed_amount': response_data.get(
                            'results', {}).get('redeemed_amount'),
                        'redeemed_points': response_data.get(
                            'results', {}).get('redeemed_points'),
                        'is_gcc_card': True,
                        'available_amount': response_data.get(
                            'results', {}).get('available_amount'),
                        'available_points': transaction_obj.available_points,
                        'payable_amount': transaction_obj.payable_amount,
                        'is_full_redemption':
                            transaction_obj.is_full_redemption,
                        'is_payment_verified': is_payment_verified,
                    }
                    self.update_youpay_transaction_data(update_data)
                    return response_data, transaction_obj
                else:
                    logger.error(
                        "Error response received from verify api call "
                        "to b2cpayback {}".format(response.text))
                    return response_data, None
            except Exception as e:
                logger.error(
                    "Verify api call to b2cpayback failed", exc_info=e)
                return None, None
        else:
            logger.error("Invalid transaction id received for b2cpayback "
                         "verify api")
            return None, None
