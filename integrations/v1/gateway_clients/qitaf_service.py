import json
import logging
from decimal import Decimal

import requests

from core.constants import REQUEST_METHOD_POST, PAYMENT_GATEWAY_B2CPAYBACK, \
    REQUEST_METHOD_GET
from core.messages import IS_REDIRECT, REDIRECT_URL, IS_SUCCESS
from core.utils import (get_payment_gateway_config, get_app_config,
                        decrypt_string)
from integrations.constants import (
    QITAF_OTP_GENERATION_API, QITAF_EARN_POINTS_API, QITAF_REDEEM_POINTS_API,
    QITAF_REVERSE_POINTS_API, QITAF_REWARD_UPDATE_API, B2CP_CACHE_KEY,
    B2CPAYBACK_HUB_CODE, PAYMENT_REQUEST_TYPE_PAYMENT,
    PAYMENT_REQUEST_REDEMPTION, PAYMENT_REQUEST_VERIFY, QITAF_HEADERS,
    QITAF_VERIFY_API, QITAF_HUB_CODE
)
from integrations.v1.gateway_clients.utils import format_qitaf_verify_data
from integrations.v1.serializers.qitafpg_serializer import (
    QitafPaymentRequestSerializer
)
from payments.constants import (PAYMENT_STATUS_PAID,
                                PAYMENT_STATUS_DECLINED_RETRY,
                                PAYMENT_METHOD_TOUCHPOINTS,
                                PAYMENT_METHOD_TOUCHPOINTS_AND_CARD,
                                PAYMENT_STATUS_PENDING)
from payments.serializers.youpay_payments import (
    YouPayTransactionDataSerializer)
from services.v1.views.common import add_payment_gateway_info_in_url
from services.v1.views.payment import PaymentRequestView
from services.v1.views.payment_handlers import PaymentHandlers

logger = logging.getLogger(__name__)


class QitafServiceManager(PaymentHandlers, PaymentRequestView):
    """
    Class to manage qitaf related operations
    """

    def __init__(self):
        self.qitaf_config = get_payment_gateway_config(B2CP_CACHE_KEY,
                                                       B2CPAYBACK_HUB_CODE)
        self.transaction_id = None
        self.transaction_obj = None
        self.request_data = {}
        self.response_data = {}
        self.request_method = None
        self.request_type = None
        self.payment_status = None
        self.payment_method = None
        self.approved = False
        self.payment_gateway = PAYMENT_GATEWAY_B2CPAYBACK

    def get_qitaf_payment_data(self, data):
        if data.get('transaction_obj'):
            payment_data = QitafPaymentRequestSerializer(data)
            return payment_data.data
        else:
            logger.error(
                "transaction_data or request_data or token_type data "
                "is not available")
            return None

    def update_qitaf_phone_number(self, data):
        """
        To update qitaf phone number
        """
        try:
            return self.update_youpay_transaction_data(data)
        except Exception as e:
            error = "Exception in update_qitaf_phone_number: {}".format(e)
            logger.error(error)
            return False

    def get_payment_header(self):
        """
        Returns headers
        """
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.qitaf_config.api_key,
            'X-API-KEY': self.qitaf_config.api_key
        }
        return headers

    def generate_otp(self, data):
        """
        calls qitaf otp generating api and returns otp
        """
        try:
            request_data = data['request_data']
            self.transaction_obj = request_data.get('transaction_obj')
            self.transaction_id = self.transaction_obj.transaction_id
            payload = self.get_qitaf_payment_data(request_data)

            data = {
                'transaction_id': str(self.transaction_id),
                'qitaf_phone_number': request_data.get("mobile_number"),
                'is_qitaf_enabled': str(True)
            }

            self.update_qitaf_phone_number(data)

            payload.update(data)
            self.request_data = payload
            payload['MSISDN'] = payload['qitaf_phone_number']
            logger.info(
                "Youpay sending request data to qitaf generate otp api "
                "is {}".format(payload))
            url = self.qitaf_config.domain + QITAF_OTP_GENERATION_API
            headers = self.get_payment_header()

            response = requests.post(url, data=json.dumps(payload),
                                     headers=headers)
            logger.info("Response from Qitaf service {}".format(response))
            if response:
                response_data = response.json()
                logger.info("qitaf payment response: {}".format(
                    response_data))
                self.response_data = response_data
                self.update_youpay_transaction_data({
                    'transaction_id': self.transaction_obj.transaction_id,
                    'payment_reference': response_data.get(
                        'payment_reference'),
                })

                return response_data, self.SUCCESS

            logger.error("Error in qitaf otp, {}".format(response.json()))
            self.response_data = response.json()

            return ({"error": response.json()},
                    self.QITAF_CONNECTION_ERROR)

        except Exception as e:
            error = "Exception in qitaf generate otp api: {}".format(e)
            logger.error(error, exc_info=True)
            self.response_data = {}
            return {"error": error}, self.QITAF_CONNECTION_ERROR
        finally:
            self.create_youpay_to_payment_gateways_data(
                transaction_obj=self.transaction_obj,
                transaction_id=self.transaction_id,
                request_data=json.dumps(self.request_data),
                response_data=json.dumps(self.response_data),
                request_method=REQUEST_METHOD_POST,
                request_type=PAYMENT_REQUEST_TYPE_PAYMENT,
            )

    def collect_points(self, data):
        """
        calls qitaf points collecting api
        """
        try:
            request_data = data['request_data']
            logger.info(
                "Youpay sending request data to qitaf point collection api "
                "is {}".format(request_data))
            payload = json.dumps(request_data)
            url = self.qitaf_config.domain + QITAF_EARN_POINTS_API
            headers = self.get_payment_header()
            response = requests.post(url, data=payload, headers=headers)
            logger.info("Response from qitaf point collection api {}"
                        "".format(response))
            if response:
                response_data = response.json()
                logger.info("qitaf point collection api response: {}".format(
                    response_data))
                return response_data, self.SUCCESS

            logger.error("Error in qitaf point collection api, {}"
                         "".format(response.text))
            return {"error": response.text}, self.QITAF_CONNECTION_ERROR

        except Exception as e:
            error = "Error in qitaf point collection api: {}".format(e)
            logger.error("Exception in qitaf point collection api: "
                         "{}".format(e))
            return {"error": error}, self.QITAF_CONNECTION_ERROR

    def determine_full_or_partial_redemption(self, **kwargs):
        """
        Todo move to b2c qitaf
        abs(payment_amount - invoice_amount) <= 3, TODO
        """
        try:
            selected_amount = Decimal(kwargs.get('selected_amount', 0))
            checkout_amount = Decimal(kwargs.get('checkout_amount', 0))
            total_amount = kwargs.get("amount")

            if selected_amount == total_amount:
                self.payment_method = PAYMENT_METHOD_TOUCHPOINTS
            elif (selected_amount + checkout_amount) == total_amount:
                self.payment_method = PAYMENT_METHOD_TOUCHPOINTS_AND_CARD
            return self.payment_method
        except Exception as e:
            logger.error(
                "UNABLE TO DETERMINE PAYMENT METHOD : {} ".format(str(e)))
            return None

    def redeem_points(self, data):
        """
        calls qitaf points redeem api

        "amount":100,
        "pin_number": 1231,
        "mobile_number":551601275,
        """
        try:
            self.request_data = data
            self.transaction_obj = self.request_data.get('transaction_obj')
            selected_amount = self.request_data.get('selected_amount')

            # self.payment_method = self.determine_full_or_partial_redemption(
            #     selected_amount=selected_amount,
            #     amount=self.transaction_obj.amount
            # )
            # todo move to separate function
            self.transaction_id = self.transaction_obj.transaction_id
            payload = self.request_data

            serializer = YouPayTransactionDataSerializer(self.transaction_obj)
            transaction_data = serializer.data
            payload.update({
                "response_url": add_payment_gateway_info_in_url(
                    transaction_data=transaction_data,
                    app_config=get_app_config(),
                    params=('?id=' + self.request_data.get("encrypted_id") +
                            "&redemption_reference_id=" + transaction_data.get(
                                "payment_reference") + "&redemption_partner=QITAF"),
                    code=QITAF_HUB_CODE,
                ),
                "invoice_id": self.transaction_obj.invoice_id,
                "customer_ip_address": self.transaction_obj.ip,
                # "channel_code": "TEST"
            })
            payload.pop('transaction_obj')
            url = self.qitaf_config.domain + QITAF_REDEEM_POINTS_API
            headers = self.get_payment_header()
            logger.info(
                "Youpay sending request data to qitaf redeem point api "
                "is {}".format(payload))
            response = requests.post(url, data=json.dumps(payload),
                                     headers=headers)
            logger.info("Response from qitaf redeem point api {}"
                        "".format(response.text))

            if response:
                response_data = response.json()
                self.response_data = response_data

                """sample success response to figureout success case
                response_data = {
                    "status": True,
                    "reason": "Success",
                    "code": 1000,
                    "message": "API request completed successfully",
                    "proceed": True,
                    "retry_same": False,
                    "retry_new": False,
                    "reverse": False
                }
                """
                logger.info(
                    "qitaf redeem point api response: {}".format(
                        response_data))
                # update redirection and save payment status
                response_data = self.handle_qitaf_response(
                    response_data, self.transaction_obj)
                return response_data, self.SUCCESS

            logger.error("\n\nError in qitaf redeem point api, {}"
                         "".format(response.text))
            self.response_data = response.json()
            response_data = self.handle_qitaf_response(
                response.json(), self.transaction_obj)
            return response_data, self.QITAF_CONNECTION_ERROR

        except Exception as e:
            error = "Exception in qitaf redeem point api: {}".format(e)
            logger.error("Exception in qitaf redeem point api: "
                         "{}".format(e))
            return {"errors": error}, self.QITAF_CONNECTION_ERROR

        finally:
            self.create_youpay_to_payment_gateways_data(
                transaction_obj=self.transaction_obj,
                transaction_id=self.transaction_id,
                request_data=json.dumps(self.request_data),
                response_data=json.dumps(self.response_data),
                request_method=REQUEST_METHOD_POST,
                request_type=PAYMENT_REQUEST_REDEMPTION,
            )

    def reverse_points(self, data):
        """
        calls qitaf points reverse api
        """
        try:
            request_data = data['request_data']
            logger.info(
                "Youpay sending request data to qitaf reverse point api "
                "is {}".format(request_data))
            payload = json.dumps(request_data)
            url = self.qitaf_config.domain + QITAF_REVERSE_POINTS_API
            headers = self.get_payment_header()
            response = requests.post(url, data=payload, headers=headers)
            logger.info("Response from qitaf reverse point api {}"
                        "".format(response))
            if response:
                response_data = response.json()
                logger.info("qitaf reverse point api response: {}".format(
                    response_data))
                self.response_data = response_data

                return response_data, self.SUCCESS

            logger.error("Error in qitaf reverse point api, {}"
                         "".format(response.text))
            self.response_data = response.json()
            return {"error": response.text}, self.QITAF_CONNECTION_ERROR

        except Exception as e:
            error = "Error in qitaf reverse point api: {}".format(e)
            logger.error("Exception in qitaf reverse point api: "
                         "{}".format(e), exc_info=True)
            return {"error": error}, self.QITAF_CONNECTION_ERROR

    def reward_update(self, data):
        """
        calls qitaf reward update api
        """
        try:
            request_data = data['request_data']
            logger.info(
                "Youpay sending request data to qitaf reward update api "
                "is {}".format(request_data))
            payload = json.dumps(request_data)
            url = self.qitaf_config.domain + QITAF_REWARD_UPDATE_API
            headers = self.get_payment_header()
            response = requests.post(url, data=payload, headers=headers)
            logger.info("Response from qitaf reward update api {}"
                        "".format(response))
            if response:
                response_data = response.json()
                logger.info("qitaf reward update api response: {}".format(
                    response_data))
                return response_data, self.SUCCESS

            logger.error("Error in qitaf reward update api, {}"
                         "".format(response.text))
            return {"error": response.text}, self.QITAF_CONNECTION_ERROR

        except Exception as e:
            error = "Error in qitaf reward update api: {}".format(e)
            logger.error("Exception in qitaf reward update api: "
                         "{}".format(e))
            return {"error": error}, self.QITAF_CONNECTION_ERROR

    def handle_qitaf_response(self, response_data, payment_data):
        is_success, is_redirect, redirect_url = False, False, None
        update_data = {}
        '''
        {'url': 'https://api.sandbox.checkout.com/sessions-interceptor/sid_cyr5xswa5afe7jpf5rraqfjkj4',
            'is_full_redemption': False, 'reference_id': '6TKX3RV54TL7LB'}
        '''
        is_full_redemption = response_data.get("is_full_redemption", False)
        if is_full_redemption is False:
            redirect_url = response_data.get('url')
            is_success = True
            is_redirect = True
            self.payment_status = PAYMENT_STATUS_PENDING
        else:
            if str(response_data.get('response_code')) in ["0"]:
                '''Qitaf full redemption Success case'''
                self.payment_status = PAYMENT_STATUS_PAID
                self.approved = True

                redirect_url = payment_data.success_url
                is_success, is_redirect = True, True

            else:
                '''Qitaf full redemption Failure case'''
                self.payment_status = PAYMENT_STATUS_DECLINED_RETRY
                is_redirect = False

        self.payment_method = (
            PAYMENT_METHOD_TOUCHPOINTS if
            response_data.get("redemption_method") == "full" else
            PAYMENT_METHOD_TOUCHPOINTS_AND_CARD)
        # todo

        update_data.update({
            "transaction_id": payment_data.transaction_id,
            "payment_status": self.payment_status,
            "approved": self.approved,
            "payment_method": self.payment_method,
            "payment_gateway": self.payment_gateway,
            "response_summary": response_data.get('reason')

        })

        self.update_youpay_transaction_data(update_data)
        return_response = {
            "message": "API request completed successfully",
            REDIRECT_URL: redirect_url,
            IS_REDIRECT: is_redirect,
            "qitaf_response": response_data,
            "is_success": is_success
        }
        return return_response

    def verification(self, request_data):
        request_transaction_id = request_data.get('transaction_id')
        if request_transaction_id:
            try:
                transaction_obj = self.get_youpay_transaction_data(
                    decrypt_string(request_transaction_id))
                formatted_data = format_qitaf_verify_data(
                    request_data, transaction_obj)
                gateway_obj = get_payment_gateway_config(
                    # QITAF_CACHE_KEY, QITAF_HUB_CODE)
                    B2CP_CACHE_KEY, B2CPAYBACK_HUB_CODE)
                qitaf_domain = gateway_obj.domain
                # TODO : CHANGE TO QITAF
                url = qitaf_domain + QITAF_VERIFY_API
                formatted_data.pop("transaction_id")

                response = requests.get(url, params=formatted_data,
                                        headers=QITAF_HEADERS)
                logger.info("Response from qitaf verify api : {}, params {}"
                            " data --- {},".format(url, formatted_data,
                                                   response.text))
                return_response_data = {}
                if response.status_code == 200:

                    #     Redemption verified successfully
                    response_data = response.json()
                    return_response_data["is_redirect"] = True
                    return_response_data[
                        "redirect_url"] = transaction_obj.success_url
                    approved = response_data.get("approved", False)
                    is_flagged = response_data.get("is_flagged", False)
                    is_gcc_card = response_data.get("is_gcc_card", False)

                    payment_status = PAYMENT_STATUS_PAID
                    return_response_data[IS_SUCCESS] = True
                else:
                    #     Redemption failed
                    payment_status = PAYMENT_STATUS_DECLINED_RETRY
                    return_response_data[IS_SUCCESS] = False
                    return_response_data['is_redirect'] = False
                    return_response_data['redirect_url'] = None
                    approved = False
                    is_flagged = False
                    is_gcc_card = False
                    response_data = response.json()

                return_response_data["payment_status"] = payment_status

                self.create_youpay_to_payment_gateways_data(
                    transaction_obj=transaction_obj,
                    transaction_id=transaction_obj.transaction_id,
                    request_data=json.dumps(formatted_data),
                    response_data=json.dumps(response_data),
                    request_method=REQUEST_METHOD_GET,
                    request_type=PAYMENT_REQUEST_VERIFY
                )
                update_data = {
                    'transaction_id': transaction_obj.transaction_id,
                    'payment_status': payment_status,
                    # 'payment_reference': (
                    #     response_data.get('payment_reference')
                    #     if response_data.get('payment_reference')
                    #     else response_data.get(
                    #         'results', {}).get('reference_id')),
                    'is_flagged': is_flagged,
                    'approved': approved,
                    # 'redeemed_amount': response_data.get(
                    #     'results', {}).get('redeemed_amount'),
                    # 'redeemed_points': response_data.get(
                    #     'results', {}).get('redeemed_points'),
                    # 'available_amount': response_data.get(
                    #     'results', {}).get('available_amount'),
                    # 'available_points': transaction_obj.available_points,
                    # 'payable_amount': transaction_obj.payable_amount,
                    'is_gcc_card': is_gcc_card,
                }
                self.update_youpay_transaction_data(update_data)
                return return_response_data, transaction_obj

            except Exception as e:
                logger.error(
                    "Verify api call to Qitaf failed", exc_info=e)
                return None, None
        else:
            logger.error("Invalid transaction id received for Qitaf "
                         "verify api")
            return None, None
