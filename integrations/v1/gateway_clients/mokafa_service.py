import json
import logging

import requests

from core.constants import REQUEST_METHOD_POST
from core.response_messages import YouPayResponse
from core.utils import get_payment_gateway_config
from integrations.constants import (
    B2CP_CACHE_KEY,
    B2CPAYBACK_HUB_CODE, PAYMENT_REQUEST_COLLECT_POINTS,
    MOKAFAA_EARN_POINTS_API, MOKAFAA_CLIENT_CODE,
    PAYMENT_REQUEST_GENERATE_OTP, MOKAFAA_OTP_GENERATION_API,
    MOKAFAA_REDEEM_POINTS_API, PAYMENT_REQUEST_REDEMPTION)
from integrations.v1.serializers.mokafaa_serializers import (
    MokafaaPaymentRequestSerializer)
from payments.constants import PAYMENT_METHOD_MOKAFAA, LANGUAGE_CODE_AR
from payments.serializers.youpay_payments import \
    YouPayTransactionDataSerializer

from services.v1.views.payment import PaymentRequestView
from services.v1.views.payment_handlers import PaymentHandlers

logger = logging.getLogger(__name__)


class MokafaServiceManager(PaymentHandlers, PaymentRequestView):
    """
    Class to manage Mokafa related operations
    """

    def __init__(self):
        self.mokafa_config = get_payment_gateway_config(B2CP_CACHE_KEY,
                                                        B2CPAYBACK_HUB_CODE)
        self.transaction_id = None
        self.transaction_obj = None
        self.request_data = {}
        self.response_data = {}

    def get_payment_header(self):
        """
        Returns headers
        """
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.mokafa_config.api_key,
            'X-API-KEY': self.mokafa_config.api_key
        }
        return headers

    def update_points_collected_mobile_number(self, data):
        """
        To update mokafa phone number
        """
        try:
            return self.update_youpay_transaction_data(data)
        except Exception as e:
            error = ("Exception in updating points_collected_mobile_number "
                     "for mokafa: {}").format(e)
            logger.error(error)
            return False

    @staticmethod
    def get_mokafaa_payment_data(data):
        """
        returns data to be passed to b2c_payback
        """
        if data.get('transaction_obj'):
            payment_data = MokafaaPaymentRequestSerializer(data)
            return payment_data.data
        else:
            logger.error(
                "transaction_data or request_data or token_type data "
                "is not available")
            return None

    def generate_otp(self, data):
        """
        calls mokafaa otp generating api and returns otp
        """
        try:
            request_data = data['request_data']
            self.transaction_obj = request_data.get('transaction_obj')
            self.transaction_id = self.transaction_obj.transaction_id
            payload = self.get_mokafaa_payment_data(request_data)
            mokafaa_phone_number = request_data.get("mobile_number")

            data = {
                'transaction_id': str(self.transaction_id),
                'mokafaa_phone_number': mokafaa_phone_number,
            }

            payload.update(data)
            self.request_data = payload
            payload['apiclient'] = self.transaction_obj.api_client.name
            payload['client_code'] = MOKAFAA_CLIENT_CODE
            logger.info(
                "Youpay sending request data to mokafaa generate otp api "
                "is {}".format(payload))
            url = self.mokafa_config.domain + MOKAFAA_OTP_GENERATION_API
            headers = self.get_payment_header()

            response = requests.post(url, data=json.dumps(payload),
                                     headers=headers)
            logger.info("Response from Mokafaa service {}".format(response))
            if response:
                response_data = response.json()
                logger.info("Mokafaa payment response: {}".format(
                    response_data))
                self.response_data = response_data
                self.update_youpay_transaction_data({
                    'transaction_id': self.transaction_obj.transaction_id,
                    'payment_reference': response_data.get(
                        'payment_reference'),
                    'points_redeemed_mobile_number': mokafaa_phone_number,
                })

                return response_data, self.SUCCESS

            logger.error("Error in mokafaa otp, {}".format(response.json()))
            self.response_data = response.json()

            return ({"error": response.json()},
                    self.MOKAFA_CONNECTION_ERROR)

        except Exception as e:
            error = "Exception in mokafaa generate otp api: {}".format(e)
            logger.error(error, exc_info=True)
            self.response_data = {}
            return {"error": error}, self.MOKAFA_CONNECTION_ERROR
        finally:
            self.create_youpay_to_payment_gateways_data(
                transaction_obj=self.transaction_obj,
                transaction_id=self.transaction_id,
                request_data=json.dumps(self.request_data),
                response_data=json.dumps(self.response_data),
                request_method=REQUEST_METHOD_POST,
                request_type=PAYMENT_REQUEST_GENERATE_OTP,
            )

    def collect_points(self, transaction_obj):
        """
        calls mokafa points collecting api
        """
        try:
            response_obj = YouPayResponse()
            if transaction_obj.earned_point:
                '''if already rewarded'''
                logger.info(
                    "Failed for Reward point, reward already collected "
                    "for ({}), rewarded point {}".format(
                        transaction_obj.transaction_id,
                        transaction_obj.earned_point))
                return None, response_obj.MOKAFA_ALREADY_COLLECTED

            if transaction_obj.payment_method in [
                PAYMENT_METHOD_MOKAFAA
            ]:
                paid_amount = transaction_obj.payable_amount
            else:
                paid_amount = transaction_obj.amount

            request_data = {
                "mobile_number": transaction_obj.points_collected_mobile_number,
                "cic_number": transaction_obj.points_collected_cic_number,
                "customer_email": transaction_obj.customer_email,
                "customer_name": transaction_obj.customer_name,
                "invoice_id": transaction_obj.invoice_id,
                "gateway_reference": transaction_obj.payment_reference,
                "currency": transaction_obj.currency,
                "client_code": MOKAFAA_CLIENT_CODE,
                "amount": str(paid_amount),
                "platform": transaction_obj.platform,

                "item_details_list": transaction_obj.brand_details.get(
                    "item_set", None),
                "brand_calculations": transaction_obj.brand_calculations,
                "language_code": transaction_obj.language,
                "redeemed_amount": (
                    str(transaction_obj.redeemed_amount) if
                    transaction_obj.redeemed_amount else 0),
                "apiclient":  transaction_obj.api_client.name,
                "source_payment_method": transaction_obj.payment_method
            }

            self.transaction_obj = transaction_obj
            self.transaction_id = str(self.transaction_obj.transaction_id)

            logger.info(
                "Youpay sending request data to mokafa point collection api "
                "is {}".format(request_data))

            request_data['transaction_id'] = self.transaction_id
            self.request_data = request_data

            payload = json.dumps(request_data)

            url = self.mokafa_config.domain + MOKAFAA_EARN_POINTS_API
            headers = self.get_payment_header()
            response = requests.post(url, data=payload, headers=headers)
            logger.info("Response from mokafa point collection api {}"
                        "".format(response))
            if response:
                response_data = response.json()
                self.response_data = response_data
                logger.info("mokafa point collection api response: {}".format(
                    response_data))
                return response_data, self.SUCCESS
            elif hasattr(response, 'text'):
                self.response_data = json.loads(response.text)
                logger.error("Error in mokafa point collection api, {}"
                             "".format(response.text))
                self.response_data = response.json()
                return {"error": response.text,
                        "partner_response": response.json()
                        }, self.MOKAFA_CONNECTION_ERROR
            else:
                msg = ("unable to get response from b2c_payback-mokafa for "
                       "point collection")
                logger.error(msg)
                return {"errors": msg}, self.MOKAFA_CONNECTION_ERROR

        except Exception as e:
            logger.error("Exception in mokafa point collection api: "
                         "{}".format(e), exc_info=True)
            return None, self.MOKAFA_CONNECTION_ERROR
        finally:
            self.create_youpay_to_payment_gateways_data(
                transaction_obj=self.transaction_obj,
                transaction_id=self.transaction_id,
                request_data=json.dumps(self.request_data),
                response_data=json.dumps(self.response_data),
                request_method=REQUEST_METHOD_POST,
                request_type=PAYMENT_REQUEST_COLLECT_POINTS,
            )

    def redeem_points(self, data):
        """
        calls mokafaa points redeem api
        """
        try:
            self.request_data = data
            self.transaction_obj = self.request_data.get('transaction_obj')
            self.transaction_id = self.transaction_obj.transaction_id
            payload = self.request_data
            language = self.transaction_obj.language

            serializer = YouPayTransactionDataSerializer(self.transaction_obj)
            transaction_data = serializer.data
            payload.update(self.prepare_redeem_payload(transaction_data))
            payload.pop('transaction_obj')
            source_payment_method = PAYMENT_METHOD_MOKAFAA
            payload.update({"source_payment_method": source_payment_method})

            verify_response, verify_status = self.verify_transaction(
                transaction_data, payment_method=PAYMENT_METHOD_MOKAFAA)
            if not verify_response:
                msg = (
                    "Youpay Mokafaa transaction verification failed for"
                    " transaction id {} response is : {} ".format(
                        self.transaction_id, verify_response))
                logger.error(msg)
                return verify_response, \
                       self.CLIENT_TRANSACTION_VERIFICATION_FAILED

            is_verified = verify_response.get('is_verified', False)
            if not is_verified and verify_response:
                msg = (
                    "Youpay Mokafaa transaction verification failed for"
                    " transaction id {} response is : {} ".format(
                        self.transaction_id, verify_response))
                logger.error(msg)
                self.response_data = verify_response
                return verify_response, \
                       self.CLIENT_TRANSACTION_VERIFICATION_FAILED

            url = self.mokafa_config.domain + MOKAFAA_REDEEM_POINTS_API
            headers = self.get_payment_header()

            logger.info(
                "Youpay sending request data to mokafaa redeem point api is {}"
                " headers {} ".format(payload, headers))

            response = requests.post(url, data=json.dumps(payload),
                                     headers=headers)

            if response:
                response_data = response.json()
                self.response_data = response_data
                logger.info("mokafaa redeem point api response: {}".format(
                    response_data))
                response_data = self.handle_mokafaa_response(
                    response_data, self.transaction_obj, self.request_data)
                return response_data, self.SUCCESS
            elif response.status_code == 400:
                response_data = response.json()
                self.response_data = response_data
                response_data = self.handle_mokafaa_response(
                    response_data, self.transaction_obj, self.request_data)
                logger.info("mokafaa redeem point api response: {} for {}"
                            "".format(response_data, self.transaction_id))
                return response_data, self.PAYMENT_FAILED
            elif response.status_code == 403:
                msg = "Mokafaa Forbidden, or partial redemption not supported"
                logger.error("{}, {}".format(msg, response.text))
                return {"errors": msg}, self.MOKAFA_NOT_SUPPORTED
            else:
                logger.error("Error in mokafaa redeem point api, {}"
                             "".format(response.text))
                self.response_data = response.json()
                if language == LANGUAGE_CODE_AR:
                    message = self.response_data.get("response_text_ar")
                else:
                    message = self.response_data.get("response_text")

                err_obj = {
                    "message": message,
                    "code": self.response_data.get("response_code"),
                    "is_full_redemption": self.response_data.get(
                        "is_full_redemption")
                }
                return {"errors": err_obj}, self.MOKAFA_CONNECTION_ERROR

        except Exception as e:
            error = "Exception in mokafaa redeem point api: {}".format(e)
            logger.error("Exception in mokafaa redeem point api: "
                         "{}".format(e), exc_info=True)
            return {"errors": error}, self.MOKAFA_CONNECTION_ERROR

        finally:
            self.create_youpay_to_payment_gateways_data(
                transaction_obj=self.transaction_obj,
                transaction_id=self.transaction_id,
                request_data=json.dumps(self.request_data),
                response_data=json.dumps(self.response_data),
                request_method=REQUEST_METHOD_POST,
                request_type=PAYMENT_REQUEST_REDEMPTION,
            )
