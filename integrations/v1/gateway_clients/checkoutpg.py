import copy
import json
import logging
from urllib.parse import urlencode

import requests
from rest_framework import status

from core.constants import (PAYMENT_GATEWAY_CHECKOUTPG, REQUEST_METHOD_POST,
                            REQUEST_METHOD_GET)
from core.messages import IS_REDIRECT, IS_SUCCESS
from core.utils import (get_checkoutpg_config,
                        process_checkoutpg_response_verification,
                        get_channel_code, get_gateway_additional_fee)
from integrations.constants import (CHECKOUTPG_CONFIG_ENDPOINT_V2,
                                    CHECKOUTPG_SAVED_CARD_ENDPOINT_V2,
                                    CHECKOUTPG_SAVED_CARD_ENDPOINT,
                                    CHECKOUTPG_PAYMENT_ENDPOINT,
                                    CHECKOUTPG_PAYMENT_VERIFICATION_ENDPOINT,
                                    PAYMENT_REQUEST_TYPE_PAYMENT,
                                    CHECKOUTPG_CREATE_TRANSACTION_ENDPOINT,
                                    PAYMENT_REQUEST_CREATE_TRANSACTION,
                                    CHECKOUTPG_KEY_AND_SECRET_ENDPOINT_V2,
                                    CHECKOUTPG_HUB_CODE,
                                    PAYMENT_REQUEST_CREATE_SESSION,
                                    PAYMENT_REQUEST_SUBMIT_SESSION,
                                    PAYMENT_DECLINED_STATUS,
                                    SOFT_DECLINE_RANGE,
                                    CHECKOUTPG_SAVED_CARD_ENDPOINT_V3,
                                    ADDITIONAL_AMEX_CARD_FEE
                                    )
from integrations.constants import (
    PAYMENT_REQUEST_TYPE_CARD,
    PAYMENT_REQUEST_TYPE_SAVED_CARD,
    PAYMENT_REQUEST_VERIFY, )
from integrations.messages import CHECKOUTPG_CONNECTION_ERROR_MESSAGE
from integrations.v1.serializers.checkoutpg_payment_request import (
    CheckoutPaymentRequestSerializer)
from payments.constants import (PAYMENT_STATUS_AUTHORIZED,
                                PAYMENT_STATUS_NONE, PAYMENT_STATUS_PAID,
                                PAYMENT_STATUS_PENDING,
                                PAYMENT_METHOD_SAVED_CARD,
                                PAYMENT_METHOD_CARD, PAYMENT_METHOD_PAYPAL,
                                PAYMENT_METHOD_APPLEPAY,
                                CREATE_SESSION_ENDPOINT,
                                SUBMIT_SESSION_ENDPOINT,
                                PAYMENT_OPTION_CARD, PAYMENT_STATUS_DECLINED,
                                PAYMENT_STATUS_DECLINED_RETRY
                                )
from services.v1.views.common import AdditionalChargesUpdation
from services.v1.views.payment import PaymentRequestView
from services.v1.views.payment_handlers import PaymentHandlers
from .utils import get_response_url
from services.constants import TOKEN_TYPE_CARD
from services.v1.views.utils import get_checkout_amex_additional_fee

logger = logging.getLogger(__name__)


class CheckoutpgManager(PaymentRequestView, PaymentHandlers):

    def __init__(self):
        self.checkoutpg_config = get_checkoutpg_config()
        self.transaction_id = None
        self.payment_method = None
        self.payment_gateway = PAYMENT_GATEWAY_CHECKOUTPG
        self.payment_status = None
        self.payment_reference = None
        self.channel_code = None
        self.currency = None

    def prepare_data_to_update(self, **kwargs):

        name_on_card = kwargs.get('name_on_card', '')

        data_to_update = {
            'transaction_id': self.transaction_id,
            "payment_status": self.payment_status,
            "payment_reference": self.payment_reference,
            "channel_code": self.channel_code,
            "payment_method": self.payment_method,
            "payment_gateway": self.payment_gateway,
            "name_on_card": name_on_card,
            'currency': self.currency,
        }

        return data_to_update

    def get_checkout_payment_data(self, data):
        if (data.get('transaction_data') and data.get('request_data')
                and data.get('token_type')):
            payment_data = CheckoutPaymentRequestSerializer(data)
            return payment_data.data
        else:
            logger.error(
                "transaction_data or request_data or token_type data "
                "is not available")
            return None

    def get_payment_header(self):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.checkoutpg_config.api_key,
            'Api-key': self.checkoutpg_config.api_key
        }
        return headers

    def get_configurations(self, channel_code):
        """
        Method for getting configurations
        params: currency
        response: json response from the checkoutpg
        """
        if self.checkoutpg_config:
            channel_codes = [channel_code]

            params = {'channel_code': channel_codes}
            headers = {'Api-key': self.checkoutpg_config.api_key}
            try:
                URL = (self.checkoutpg_config.domain +
                       CHECKOUTPG_CONFIG_ENDPOINT_V2)

                configurations = requests.get(url=URL, params=params,
                                              headers=headers)
                if configurations:
                    response = json.loads(configurations.text)
                    resp_status = response.get('status', False)
                    message = response.get('message', None)
                    if response and resp_status == status.HTTP_200_OK:
                        public_keys = response.get('public_keys', None)
                        checkout_mada_bins = response.get('card_bins')[0].get(
                            'bin',
                            []) if response.get(
                            'card_bins', None) else []
                        data = {'public_keys': public_keys,
                                'checkout_mada_bins': checkout_mada_bins}
                        return data, self.SUCCESS

                    return message, resp_status
                logger.error("Unable to fetch Checkoutpg configurations.")
                return None, self.CHECKOUTPG_CONNECTION_ERROR
            except Exception as e:
                logger.error(
                    "Failed to fetch the checkoutpg v2 configuration "
                    "data {}".format(e))
                return None, self.CHECKOUTPG_CONNECTION_ERROR
        else:
            logger.error(CHECKOUTPG_CONNECTION_ERROR_MESSAGE)
            return None, self.CHECKOUTPG_CONNECTION_ERROR

    def get_key_and_secret(self, currency):
        """
        Method for getting key and secret
        """
        if self.checkoutpg_config:
            channel_codes = []
            channel_code = get_channel_code(self.transaction_obj)
            channel_codes.append(channel_code)

            params = {'channel_code': channel_codes}
            headers = {'Api-key': self.checkoutpg_config.api_key}
            try:
                URL = (self.checkoutpg_config.domain +
                       CHECKOUTPG_KEY_AND_SECRET_ENDPOINT_V2)
                key_and_secret_response = requests.get(url=URL, params=params,
                                                       headers=headers)
                if key_and_secret_response:
                    response = json.loads(key_and_secret_response.text)
                    resp_status = response.get('status', False)
                    if response and resp_status == status.HTTP_200_OK:
                        key_and_secret = response.get('key_and_secret', None)

                        data = key_and_secret
                        return data, self.SUCCESS
                logger.error("Unable to fetch Checkoutpg configurations.")
                return None, self.CHECKOUTPG_CONNECTION_ERROR
            except Exception as e:
                logger.error(
                    "Failed to fetch the checkoutpg v2 configuration "
                    "data {}".format(e))
                return None, self.CHECKOUTPG_CONNECTION_ERROR
        else:
            logger.error(CHECKOUTPG_CONNECTION_ERROR_MESSAGE)
            return None, self.CHECKOUTPG_CONNECTION_ERROR

    def get_saved_cards(self, email, currency, channel_code=None):
        """
        Method for getting saved cards
        """
        if self.checkoutpg_config:
            saved_cards = []
            try:
                PARAMS = {'key': self.checkoutpg_config.api_key,
                          'email': email,
                          'currency': currency,
                          'channel_code': channel_code}
                URL = self.checkoutpg_config.domain + CHECKOUTPG_SAVED_CARD_ENDPOINT_V2
                saved_cards = requests.get(url=URL, params=PARAMS)
                if saved_cards:
                    saved_cards = json.loads(saved_cards.text).get('cards')
                    for card in saved_cards:
                        card['key'] = CHECKOUTPG_HUB_CODE
                return saved_cards

            except Exception as e:
                logger.error(
                    "Unable to fetch saved card details for user {0} "
                    "because, {1}".format(email, str(e)))
                return None
        else:
            logger.error(CHECKOUTPG_CONNECTION_ERROR_MESSAGE)
            return None, None

    def get_saved_cards_v3(self, email, currency, channel_code=None,
                           customer_uid=None, client_code=None):
        """
        Method for getting saved cards
        """
        if self.checkoutpg_config:
            saved_cards = []
            try:
                PARAMS = {'key': self.checkoutpg_config.api_key,
                          'email': email,
                          'currency': currency,
                          'channel_code': channel_code,
                          'customer_uid': customer_uid,
                          'client_code': client_code}
                URL = self.checkoutpg_config.domain + CHECKOUTPG_SAVED_CARD_ENDPOINT_V3
                saved_cards = requests.get(url=URL, params=PARAMS)
                if saved_cards:
                    saved_cards = json.loads(saved_cards.text).get('cards')
                    for card in saved_cards:
                        card['key'] = CHECKOUTPG_HUB_CODE
                return saved_cards

            except Exception as e:
                logger.error(
                    "Unable to fetch saved card details for user {0} "
                    "because, {1}".format(email, str(e)))
                return None
        else:
            logger.error(CHECKOUTPG_CONNECTION_ERROR_MESSAGE)
            return None, None

    def delete_saved_card(self, card_id):
        checkoutpg_config = get_checkoutpg_config()
        if checkoutpg_config:
            try:
                header = self.get_payment_header()
                URL = (
                        self.checkoutpg_config.domain + CHECKOUTPG_SAVED_CARD_ENDPOINT +
                        card_id + '/')
                response = requests.delete(url=URL, headers=header)
                return json.loads(response.text)
            except Exception as e:
                logger.error(
                    "Unable to delete saved card {0} details because, {1}"
                    .format(card_id, str(e)))
        else:
            logger.error(CHECKOUTPG_CONNECTION_ERROR_MESSAGE)
            return None, None

    def delete_saved_card_v2(self, email, channel_code):
        checkoutpg_config = get_checkoutpg_config()
        if checkoutpg_config:
            try:
                header = self.get_payment_header()
                query_params = urlencode(
                    {"email": email, "channel_code": channel_code})
                URL = (
                        self.checkoutpg_config.domain +
                        CHECKOUTPG_SAVED_CARD_ENDPOINT_V2 + "deactivate/?" + query_params)
                response = requests.delete(url=URL, headers=header)
                return json.loads(response.text)
            except Exception as e:
                logger.error(
                    "Unable to delete saved card {0} details because, {1}"
                    .format(email, str(e)))
        else:
            logger.error(CHECKOUTPG_CONNECTION_ERROR_MESSAGE)
            return None, None

    def delete_saved_card_v3(self, email, channel_code, customer_uid=None):
        checkoutpg_config = get_checkoutpg_config()
        if checkoutpg_config:
            try:
                header = self.get_payment_header()
                query_params = urlencode(
                    {"email": email, "channel_code": channel_code,
                     "customer_uid": customer_uid})
                URL = (
                        self.checkoutpg_config.domain +
                        CHECKOUTPG_SAVED_CARD_ENDPOINT_V3 + "deactivate/?" + query_params)
                response = requests.delete(url=URL, headers=header)
                return json.loads(response.text)
            except Exception as e:
                logger.error(
                    "Unable to delete saved card {0} details because, {1}"
                    .format(email, str(e)))
        else:
            logger.error(CHECKOUTPG_CONNECTION_ERROR_MESSAGE)
            return None, None

    def saved_card_payment(self, data):

        transaction_data = data.get('transaction_data')
        request_data = data.get('request_data')
        self.transaction_id = transaction_data.get('transaction_id')
        self.payment_method = PAYMENT_METHOD_SAVED_CARD
        self.payment_gateway = PAYMENT_GATEWAY_CHECKOUTPG
        self.payment_status = transaction_data.get('payment_status')
        self.payment_reference = transaction_data.get('payment_reference')
        self.currency = transaction_data.get('currency')

        verify_response, verify_status = self.verify_transaction(
            transaction_data)
        logger.info(
            "Verify response: {} - {}".format(verify_status,
                                              verify_response))

        is_verified = verify_response.get('is_verified', False)

        """if transaction is verified then proceed with payment"""
        try:
            if verify_status == status.HTTP_200_OK and is_verified:

                checkoutpg_config = get_checkoutpg_config()

                if checkoutpg_config:
                    payment_data = self.get_checkout_payment_data(data)
                    transaction_obj = self.get_youpay_transaction_data(
                        self.transaction_id)
                    if request_data.get("is_amex_card", False):
                        additional_fee_obj = get_gateway_additional_fee(
                            transaction_obj.currency,
                            ADDITIONAL_AMEX_CARD_FEE,
                            CHECKOUTPG_HUB_CODE, "checkout_card")
                        additional_fee_config = (
                            get_checkout_amex_additional_fee(
                                additional_fee_obj, transaction_obj))
                        payment_data["amount"] = additional_fee_config.get(
                            'total_amount', payment_data.get("amount", "0"))
                    self.channel_code = payment_data.get('channel_code')
                    log_request_data = copy.deepcopy(payment_data)
                    log_request_data["cvv"] = "***"
                    logger.info(
                        "Youpay sending savedcard payment data for "
                        "transaction id {} is {}".format(
                            transaction_obj.transaction_id, log_request_data))
                    payment_data_to_send = json.dumps(payment_data)
                    url = (self.checkoutpg_config.domain +
                           CHECKOUTPG_PAYMENT_ENDPOINT)
                    headers = self.get_payment_header()


                    response = requests.post(url, data=payment_data_to_send,
                                             headers=headers)

                    # storing Youpay to payment gateway request and response data
                    self.create_youpay_to_payment_gateways_data(
                        transaction_obj=transaction_obj,
                        transaction_id=self.transaction_id,
                        request_data=json.dumps(log_request_data),
                        response_data=response.text,
                        request_method=REQUEST_METHOD_POST,
                        request_type=PAYMENT_REQUEST_TYPE_SAVED_CARD,
                    )

                    logger.info(
                        "Checkoutpg savedcard request response for "
                        "transaction id {} is {}".format(self.transaction_id,
                                                         response.text))

                    if response:
                        response_data_json = response.json()
                        response_data, response_code = (
                            self.handle_card_payment_response(
                                response_data_json, payment_data))
                        return response_data, response_code

                    logger.error("Error in savedcard payment, {}".format(
                        response.text))

                    return ({"error": response.json()},
                            self.CHECKOUTPG_CONNECTION_ERROR)
                else:
                    logger.error(CHECKOUTPG_CONNECTION_ERROR_MESSAGE)
                    return None, self.CHECKOUTPG_CONNECTION_ERROR
            else:
                msg = (
                    "Youpay Saved Card transaction verification failed for"
                    " transaction id {} response is : {} ".format(
                        self.transaction_id, verify_response))
                logger.error(msg)
                return verify_response, self.CLIENT_TRANSACTION_VERIFICATION_FAILED
        except Exception as e:
            logger.error(
                "Error while processing saved card payment for transaction id"
                " {}, err : {}".format(self.transaction_id, str(e)))
            return None, self.CHECKOUTPG_CONNECTION_ERROR

    def card_payment(self, data):
        transaction_data = data.get('transaction_data')

        self.transaction_id = transaction_data.get('transaction_id')
        self.payment_method = PAYMENT_METHOD_CARD
        self.payment_gateway = PAYMENT_GATEWAY_CHECKOUTPG
        self.payment_status = transaction_data.get('payment_status')
        self.payment_reference = transaction_data.get('payment_reference')
        self.currency = transaction_data.get('currency')
        
        name_on_card = ""

        verify_response, verify_status = self.verify_transaction(
            transaction_data)

        is_verified = verify_response.get('is_verified', False)

        try:
            """if transaction is verified then proceed with payment"""
            if verify_status == status.HTTP_200_OK and is_verified:
                checkoutpg_config = get_checkoutpg_config()
                if checkoutpg_config:
                    payment_data = self.get_checkout_payment_data(data)
                    name_on_card = payment_data.get('customer_name')
                    self.channel_code = payment_data.get('channel_code')
                    logger.info(
                        "Youpay sending payment data is {}".format(
                            payment_data))
                    payment_data_to_send = json.dumps(payment_data)
                    url = (self.checkoutpg_config.domain +
                           CHECKOUTPG_PAYMENT_ENDPOINT)
                    headers = self.get_payment_header()

                    transaction_obj = self.get_youpay_transaction_data(
                        self.transaction_id)

                    response = requests.post(url, data=payment_data_to_send,
                                             headers=headers)
                    # storing Youpay to payment gateway request and response data
                    self.create_youpay_to_payment_gateways_data(
                        transaction_obj=transaction_obj,
                        transaction_id=data.get('transaction_data').get(
                            'transaction_id'),
                        request_data=payment_data_to_send,
                        response_data=response.text,
                        request_method=REQUEST_METHOD_POST,
                        request_type=PAYMENT_REQUEST_TYPE_CARD,
                    )

                    logger.info(
                        "Checkoutpg card request response for transaction id "
                        "{} is {}".format(self.transaction_id, response.text))

                    if response:
                        response_data_json = response.json()
                        response_data, response_code = (
                            self.handle_card_payment_response(
                                response_data_json, payment_data,
                                is_card=True))
                        return response_data, response_code

                    logger.error(
                        "Error occurred on checkout card payments for "
                        "transaction id {}, {}".format(self.transaction_id,
                                                       response.text))
                    return None, self.CHECKOUTPG_CONNECTION_ERROR
                else:
                    logger.error(CHECKOUTPG_CONNECTION_ERROR_MESSAGE)
                    return None, self.CHECKOUTPG_CONNECTION_ERROR
            else:
                msg = (
                    "Youpay Card transaction verification failed, transaction"
                    " id {} response is : {} ".format(self.transaction_id,
                                                      verify_response))
                logger.error(msg)
                return verify_response, self.CLIENT_TRANSACTION_VERIFICATION_FAILED
        except Exception as e:
            error = ("Error while processing card payment for transaction id "
                     "{}, err : {}".format(self.transaction_id, str(e)))
            logger.error(error)
            return {"error": error}, self.CHECKOUTPG_CONNECTION_ERROR

    def handle_card_payment_response(self, response_data, payment_data,
                                     is_card=False):
        logger.info(
            "card payment response handling, checkoutpg response for "
            "transaction {} is {} ".format(
                self.transaction_id, response_data))
        if response_data.get(
                'status') == 200 and response_data.get(IS_REDIRECT) is True:
            # 3ds case
            self.payment_reference = response_data.get("reference_id")
            self.payment_status = PAYMENT_STATUS_PENDING
            name_on_card = payment_data.get('customer_name')
            self.update_youpay_transaction_data(
                self.prepare_data_to_update(name_on_card=name_on_card))

            response_data[IS_SUCCESS] = True
            response_data.pop('checkout_request_data')
            response_data.pop('checkout_response_data')
            return response_data, self.SUCCESS

        elif response_data.get('status') == 200 and not response_data.get(
                IS_REDIRECT):
            # pre-auth case
            logger.info(
                "card payment pre auth response data {} for transaction {}"
                "".format(response_data, self.transaction_id))
            is_pre_auth = True
            redirect, response_data = (
                process_checkoutpg_response_verification(
                    transaction_id=self.transaction_id,
                    response_data=response_data.get("checkout_response_data"),
                    is_pre_auth=is_pre_auth,
                    payment_method=self.payment_method,
                    payment_gateway=self.payment_gateway,
                    channel_code=self.channel_code,
                ))
            logger.info("pre auth verification method response data {} for "
                        "transaction {}".format(response_data,
                                                self.transaction_id))
            if redirect:
                response_data.pop('transaction_message')
                return response_data, self.SUCCESS
            else:
                return response_data, self.PRE_AUTH
        else:
            logger.error("card payment error occurred, response {}".format(
                response_data))
            return None, self.UNKNOWN_ERR

    def paypal_payment(self, data):
        transaction_data = data.get('transaction_data')

        self.transaction_id = transaction_data.get('transaction_id')
        self.payment_method = PAYMENT_METHOD_PAYPAL
        self.payment_gateway = PAYMENT_GATEWAY_CHECKOUTPG
        self.payment_status = transaction_data.get('payment_status')
        self.payment_reference = transaction_data.get('payment_reference')
        self.currency = transaction_data.get('currency')

        verify_response, verify_status = self.verify_transaction(
            transaction_data)

        is_verified = verify_response.get('is_verified', False)

        try:
            """if transaction is verified then proceed with payment"""
            if verify_status == status.HTTP_200_OK and is_verified:
                checkoutpg_config = get_checkoutpg_config()
                if checkoutpg_config:
                    additional_charges = (
                        self.get_additional_charges())
                    data.update(additional_charges)
                    payment_data = self.get_checkout_payment_data(data)
                    logger.info(
                        "Youpay sending paypal payment data is {}".format(
                            payment_data))
                    payment_data_to_send = json.dumps(payment_data)
                    url = self.checkoutpg_config.domain + CHECKOUTPG_PAYMENT_ENDPOINT
                    headers = self.get_payment_header()

                    transaction_obj = self.get_youpay_transaction_data(
                        self.transaction_id)

                    response = requests.post(url, data=payment_data_to_send,
                                             headers=headers)
                    # storing Youpay to payment gateway request and response data
                    self.create_youpay_to_payment_gateways_data(
                        transaction_obj=transaction_obj,
                        transaction_id=data.get('transaction_data').get(
                            'transaction_id'),
                        request_data=payment_data_to_send,
                        response_data=response.text,
                        request_method=REQUEST_METHOD_POST,
                        request_type=PAYMENT_REQUEST_TYPE_CARD,
                    )

                    logger.info(
                        "Checkoutpg paypal request response, transaction id "
                        "{} ".format(self.transaction_id))

                    if response:
                        response_data = response.json()
                        if (response_data.get('status') == 200
                                and response_data.get(IS_REDIRECT) is True):
                            self.payment_reference = response_data.get(
                                "reference_id")
                            self.payment_status = PAYMENT_STATUS_PENDING
                            data_to_update = self.prepare_data_to_update()
                            data_to_update.update(additional_charges)
                            self.update_youpay_transaction_data(
                                data_to_update)
                            response_data[IS_SUCCESS] = True
                            return response_data, self.SUCCESS

                        logger.error("Error in paypal payment, {}".format(
                            response.text))
                        data_to_update = self.prepare_data_to_update()

                        data_to_update.update(additional_charges)
                        self.update_youpay_transaction_data(data_to_update)
                        return (None,
                                self.CHECKOUTPG_CONNECTION_ERROR)
                    return None, self.CHECKOUTPG_CONNECTION_ERROR
                else:
                    logger.error(CHECKOUTPG_CONNECTION_ERROR_MESSAGE)
                    return None, self.CHECKOUTPG_CONNECTION_ERROR
            else:
                msg = (
                    "Youpay Paypal transaction verification failed for "
                    "transaction id {} response is : {} ".format(
                        self.transaction_id, verify_response))
                logger.error(msg)
                return (
                    verify_response,
                    self.CLIENT_TRANSACTION_VERIFICATION_FAILED)
        except Exception as e:
            error = (
                "Error while processing paypal payment for transaction id "
                "{}, err : {}".format(self.transaction_id, str(e)))
            logger.error(error)
            return {"error": error}, self.CHECKOUTPG_CONNECTION_ERROR

    def get_additional_charges(self):
        additional_charge_updation = AdditionalChargesUpdation()
        additional_charge_obj = (
            additional_charge_updation.get_additional_charges(
                self.transaction_id, self.payment_method)
        )
        dct_additional_charges = {}
        if additional_charge_obj:
            dct_additional_charges = {
                "additional_vat": additional_charge_obj.additional_vat,
                "additional_processing_fee": (
                    additional_charge_obj.additional_processing_fee),
                "additional_processing_fee_vat": (
                    additional_charge_obj.additional_processing_fee_vat),
                "additional_total_amount": (
                    additional_charge_obj.additional_total_amount)
            }
        return dct_additional_charges

    def verify_payment(self, data):
        url = (self.checkoutpg_config.domain +
               CHECKOUTPG_PAYMENT_VERIFICATION_ENDPOINT)
        transaction_id = data.get('transaction_id')
        youpay_transaction = self.get_youpay_transaction_data(transaction_id)

        if youpay_transaction is None:
            return None, self.TRANSACTION_NOT_FOUND

        params = {
            'cko-session-id': data.get('cko_session_id'),
            'channel_code': youpay_transaction.channel_code,
            'invoice_id': youpay_transaction.invoice_id,
            'client_id': youpay_transaction.api_client.client_code,
        }
        response = requests.get(url, params=params)
        logger.info(
            "Checkout Verify API response for transaction {} is {}"
            "".format(transaction_id, response.text))
        transaction_obj = self.get_youpay_transaction_data(transaction_id)

        # storing Youpay to payment gateway request and response data
        self.create_youpay_to_payment_gateways_data(
            transaction_obj=transaction_obj,
            transaction_id=transaction_id,
            request_data=json.dumps(params),
            response_data=response.text,
            request_type=PAYMENT_REQUEST_VERIFY,
            request_method=REQUEST_METHOD_GET,
        )

        if response:
            response_data = response.json()
            redirect, response_data = (
                process_checkoutpg_response_verification(
                    transaction_id=transaction_id,
                    response_data=response_data))
            if redirect:
                return response_data, self.SUCCESS
            else:
                return response_data, self.PAYMENT_FAILED
        else:
            logger.error(
                "Error while verifying_payment status: {}, reason {} "
                .format(response.status_code, response.json()))
            return (None,
                    self.CHECKOUTPG_CONNECTION_ERROR)

    def create_transaction_in_checkoutpg(self, request_data):
        try:
            checkoutpg_config = get_checkoutpg_config()
            if checkoutpg_config:
                payment_data = self.get_checkout_payment_data(
                    request_data)

                logger.info(
                    "Youpay sending Applepay payment data is {}".format(
                        payment_data))
                payment_data_to_send = json.dumps(payment_data)

                url = (self.checkoutpg_config.domain +
                       CHECKOUTPG_CREATE_TRANSACTION_ENDPOINT)

                headers = self.get_payment_header()

                transaction_obj = self.get_youpay_transaction_data(
                    self.transaction_id)

                checkoutpg_response = requests.post(
                    url, data=payment_data_to_send, headers=headers)

                self.channel_code = payment_data['channel_code']

                # storing Youpay to payment gateway request and response data
                self.create_youpay_to_payment_gateways_data(
                    transaction_obj=transaction_obj,
                    transaction_id=request_data.get(
                        'transaction_data').get(
                        'transaction_id'),
                    request_data=payment_data_to_send,
                    response_data=checkoutpg_response.text,
                    request_method=REQUEST_METHOD_POST,
                    request_type=PAYMENT_REQUEST_CREATE_TRANSACTION,
                )

                logger.info(
                    "Checkoutpg Applepay request response for "
                    "transaction id {} is {}".format(
                        self.transaction_id, checkoutpg_response.text))

                if checkoutpg_response:
                    checkoutpg_response_data = checkoutpg_response.json()
                    if checkoutpg_response_data.get('status') == 200:
                        self.payment_reference = checkoutpg_response_data.get(
                            "data").get("reference")

                        self.payment_status = PAYMENT_STATUS_PENDING
                        response_code = (
                            self.APPLE_PAY_STATUS_UPDATED_PENDING)

                        return None, response_code

                    logger.error("Error in paypal payment, {}".format(
                        checkoutpg_response.text))

                    return ({"error": checkoutpg_response.json()},
                            self.CHECKOUTPG_CONNECTION_ERROR)
                return None, self.CHECKOUTPG_CONNECTION_ERROR
            else:
                logger.error(CHECKOUTPG_CONNECTION_ERROR_MESSAGE)
                return None, self.CHECKOUTPG_CONNECTION_ERROR
        except Exception as e:
            logger.error("Exception in payment request : {} "
                         .format(e))
            logger.error("Exception occured : {} ".format(e))
            return None, self.CHECKOUTPG_CONNECTION_ERROR

    def applepay_update_status(self, request_data):
        transaction_data = request_data.get('transaction_data')
        payment_request_data = request_data.get('request_data')
        payment_response_data = request_data.get('response_data').get(
            'response_data')
        self.transaction_id = transaction_data.get('transaction_id')
        self.payment_method = PAYMENT_METHOD_APPLEPAY
        self.payment_reference = transaction_data.get('payment_reference')
        self.transaction_obj = request_data.get('transaction_obj')
        self.currency = transaction_data.get('currency')

        response_data = {}

        # payment_stage may be pending, authorized, paid
        payment_stage = request_data.get('payment_stage')

        logger.info("APPLE PAY Status update for {} to {} ".format(
            self.transaction_id, payment_stage))

        verify_response, verify_status = self.verify_transaction(
            transaction_data)
        logger.info(
            "Verify response: {} - {}".format(verify_status,
                                              verify_response))

        is_verified = verify_response.get('is_verified', False)

        try:

            # client verify check
            if verify_status == status.HTTP_200_OK and is_verified:

                if payment_stage == PAYMENT_STATUS_PENDING:
                    data, code = self.create_transaction_in_checkoutpg(
                        request_data)

                    self.update_youpay_transaction_data(
                        self.prepare_data_to_update())
                    return data, code

                elif payment_stage == PAYMENT_STATUS_AUTHORIZED:

                    key_and_secret_data, code = self.get_key_and_secret(
                        transaction_data.get('currency', None))
                    if key_and_secret_data:
                        response_data['key_and_secret_data'] = (
                            key_and_secret_data[0])
                    else:
                        logger.error(
                            "Error in getting key and secret data for apple "
                            "pay on transaction id {} ".format(
                                self.transaction_id))
                        return None, self.CHECKOUTPG_RESPONSE_FAILED

                    self.payment_status = PAYMENT_STATUS_AUTHORIZED
                    response_data["data"] = transaction_data

                    response_code = self.APPLE_PAY_STATUS_UPDATED_AUTHORIZED
                    message = self.MESSAGE.get(response_code)

                    self.update_youpay_transaction_data(
                        self.prepare_data_to_update())

                elif payment_stage == PAYMENT_STATUS_PAID:
                    # storing Youpay to payment gateway request and response data
                    self.create_youpay_to_payment_gateways_data(
                        transaction_obj=self.transaction_obj,
                        transaction_id=self.transaction_id,
                        request_data=json.dumps(payment_request_data),
                        response_data=json.dumps(payment_response_data),
                        request_type=PAYMENT_REQUEST_TYPE_PAYMENT,
                        request_method=REQUEST_METHOD_POST,
                    )

                    res_data = payment_response_data.get('payment')
                    # to mark status as paid
                    res_data['source'] = PAYMENT_METHOD_APPLEPAY

                    redirect, response_data = (
                        process_checkoutpg_response_verification(
                            transaction_id=self.transaction_id,
                            response_data=res_data))

                    response_code = self.APPLE_PAY_REDIRECT
                    message = self.MESSAGE.get(response_code)
                    logger.info(message)

                    self.update_youpay_transaction_data(
                        self.prepare_data_to_update())

                else:
                    message = (
                        "APPLE PAY Invalid payment stage received {} for"
                        " transaction id {}, status {}".format(
                            payment_stage,
                            self.transaction_id,
                            self.payment_status))

                    self.payment_status = PAYMENT_STATUS_NONE
                    response_code = self.APPLE_PAY_BAD_REQUEST

                logger.info(message)
                return response_data, response_code
            else:
                msg = (
                    "Youpay Applepay transaction verification failed for "
                    "transaction id {} response is : {} ".format(
                        self.transaction_id, verify_response))
                logger.error(msg)
                return verify_response, self.CLIENT_TRANSACTION_VERIFICATION_FAILED
        except Exception as e:
            logger.error("Exception in payment request : {} "
                         .format(e))
            msg = (
                "Error on processing applepay status update for transaction"
                "id {}, err : {}".format(self.transaction_id, str(e)))
            logger.error(msg)
            return None, self.APPLE_PAY_CONNECTION_ERROR

    def create_payment_session(self, transaction_obj, is_mada,
                               is_partial_payment):
        """
        Method for creating a Checkout payment session
        """
        if self.checkoutpg_config:
            amount = (transaction_obj.payable_amount if is_partial_payment
                      else transaction_obj.amount)
            request_data = {
                "amount": str(amount),
                "currency": transaction_obj.currency,
                "channel_code": get_channel_code(transaction_obj),
                "response_url": get_response_url(
                    transaction_obj, is_partial_payment),
                "customer_name": transaction_obj.customer_name,
                "customer_email": transaction_obj.customer_email,
                "order_reference": transaction_obj.order_reference,
                "country_code": transaction_obj.country_code,
                "is_mada": is_mada
            }

            try:
                url = self.checkoutpg_config.domain + CREATE_SESSION_ENDPOINT
                headers = self.get_payment_header()

                response = requests.post(url, data=json.dumps(request_data),
                                         headers=headers)

                logger.info(
                    "Checkout create session response for transaction %s: %s",
                    transaction_obj.id, response.text
                )

                self.create_youpay_to_payment_gateways_data(
                    transaction_obj=transaction_obj,
                    transaction_id=transaction_obj.transaction_id,
                    request_data=json.dumps(request_data),
                    response_data=response.text,
                    request_method=REQUEST_METHOD_POST,
                    request_type=PAYMENT_REQUEST_CREATE_SESSION,
                )

                if response:
                    response_data = response.json()
                    response_data.pop('status', None)
                    return response_data, self.SUCCESS
                logger.error(
                    "Checkout session creation failed for transaction %s: %s",
                    transaction_obj.transaction_id, response.text
                )
                return None, self.PAYMENT_FAILED

            except Exception as e:
                logger.error(
                    "Unable to create checkout session for user %s because %s",
                    transaction_obj.customer_email, str(e)
                )
                return None, self.PAYMENT_FAILED
        else:
            logger.error(CHECKOUTPG_CONNECTION_ERROR_MESSAGE)
            return None, self.PAYMENT_FAILED

    def submit_payment_session(self, transaction_obj, request_data):
        """
        Method for submitting a Checkout payment session
        """
        amount = str(transaction_obj.amount)
        is_amex_card = request_data.get('is_amex_card', False)
        additional_vat_percentage = transaction_obj.additional_vat_percentage
        if is_amex_card:
            logger.info(
                "Card payment with Amex card, calculating additional fee for "
                "transaction {}".format(transaction_obj.transaction_id))
            additional_fee_obj = get_gateway_additional_fee(
                transaction_obj.currency, ADDITIONAL_AMEX_CARD_FEE,
                CHECKOUTPG_HUB_CODE, "checkout_card")
            additional_fee_config = (
                get_checkout_amex_additional_fee(
                    additional_fee_obj, transaction_obj))
            amount = additional_fee_config.get('total_amount', amount)
            additional_vat_percentage = additional_fee_obj.VAT_percentage
        if self.checkoutpg_config:
            is_save_user_token = request_data.get('is_save_user_token', False)
            channel_code = get_channel_code(transaction_obj)

            payment_request_data = {
                "session_data": request_data.get('session_data'),
                "session_id": request_data.get('session_id'),
                "is_save_user_token": is_save_user_token,
                "customer_name": request_data.get('customer_name'),
                "amount": amount,
                "order_reference": transaction_obj.order_reference,
                "currency": transaction_obj.currency,
                "customer_email": transaction_obj.customer_email,
                "amount_in_aed": str(transaction_obj.amount_in_aed),
                "invoice_id": transaction_obj.invoice_id,
                "order_id": transaction_obj.order_id,
                "token_type": TOKEN_TYPE_CARD,
                "channel_code": channel_code,
                "client_code": transaction_obj.api_client.client_code,
                "customer_ip_address": transaction_obj.ip,
                "is_mada": request_data.get('is_mada', False),
                "customer_uid": transaction_obj.customer_uid
            }
            try:
                url = self.checkoutpg_config.domain + SUBMIT_SESSION_ENDPOINT
                headers = self.get_payment_header()

                response = requests.post(url, data=json.dumps(
                    payment_request_data), headers=headers)

                logger.info(
                    "Checkout submit session response for transaction %s: %s",
                    transaction_obj.id, response.text
                )

                self.create_youpay_to_payment_gateways_data(
                    transaction_obj=transaction_obj,
                    transaction_id=transaction_obj.transaction_id,
                    request_data=json.dumps(payment_request_data),
                    response_data=response.text,
                    request_method=REQUEST_METHOD_POST,
                    request_type=PAYMENT_REQUEST_SUBMIT_SESSION,
                )

                if response:
                    response_data = response.json()

                    transaction_data = {
                        "transaction_id": transaction_obj.transaction_id,
                        "payment_status": PAYMENT_STATUS_PENDING,
                        "payment_reference": response_data.get('reference_id'),
                        "payment_method": PAYMENT_OPTION_CARD,
                        "payment_gateway": PAYMENT_GATEWAY_CHECKOUTPG,
                        "name_on_card": request_data.get("customer_name"),
                        "channel_code": channel_code,
                        "additional_vat_percentage": additional_vat_percentage
                    }
                    response_data.pop('reference_id', None)

                    status = response_data.get('status', '')
                    if status == PAYMENT_DECLINED_STATUS:
                        declined_response = self.handle_submit_session_response(
                            response_data, transaction_obj
                        )

                        if declined_response.get("redirect_url"):
                            transaction_data["payment_status"] = (
                                PAYMENT_STATUS_DECLINED)
                        else:
                            transaction_data["payment_status"] = (
                                PAYMENT_STATUS_DECLINED_RETRY)

                        self.update_youpay_transaction_data(transaction_data)
                        return declined_response, self.PRE_AUTH

                    self.update_youpay_transaction_data(transaction_data)
                    return response_data, self.SUCCESS

                logger.error(
                    "Checkout session submission failed for transaction %s: %s",
                    transaction_obj.transaction_id, response.text
                )
                return None, self.PAYMENT_FAILED

            except Exception as e:
                logger.error(
                    "Unable to submit checkout session for user %s because %s",
                    transaction_obj.customer_email, str(e)
                )
                return None, self.PAYMENT_FAILED
        else:
            logger.error(CHECKOUTPG_CONNECTION_ERROR_MESSAGE)
            return None, self.PAYMENT_FAILED

    def handle_submit_session_response(self, response_data, transaction_obj):
        """
        Method for handling submit session response
        """
        decline_reason = response_data.get('decline_reason')
        decline_category = response_data.get('decline_category')

        is_redirect_flag = decline_category != SOFT_DECLINE_RANGE
        redirect_url = None
        code = self.PRE_AUTH

        if is_redirect_flag:
            redirect_url = ('{}?transaction_id={}'.format(
            transaction_obj.failure_url, transaction_obj.transaction_id))
            code = self.PAYMENT_FAILED

        response = {
            IS_REDIRECT: is_redirect_flag,
            "redirect_url": redirect_url,
            IS_SUCCESS: False,
            "message": decline_reason,
            "code": code
        }

        return response
