import inspect
import json
import logging

import requests
from django.db.models import Q
from rest_framework import status

from core.constants import (REQUEST_METHOD_POST, PAYMENT_GATEWAY_B2CPAYBACK,
                            REQUEST_METHOD_GET, LANGUAGE_ENGLISH)
from core.messages import IS_REDIRECT, REDIRECT_URL, IS_SUCCESS
from core.utils import (get_payment_gateway_config, get_app_config,
                        decrypt_string,
                        auto_enable_or_disable_point_collection,
                        get_channel_code,
                        get_config_from_payment_configurations)
from integrations.constants import (
    QITAF_OTP_GENERATION_API, QITAF_EARN_POINTS_API, QITAF_REDEEM_POINTS_API,
    QITAF_REVERSE_POINTS_API, QITAF_REWARD_UPDATE_API, B2CPAYBACK_HUB_CODE,
    PAYMENT_REQUEST_REDEMPTION, PAYMENT_REQUEST_VERIFY,
    QITAF_HEADERS,
    QITAF_VERIFY_API, QITAF_HUB_CODE, PAYMENT_REQUEST_GENERATE_OTP,
    PAYMENT_REQUEST_COLLECT_POINTS,
    CHECKOUT_SAUDI_CURRENCY, QITAF_CACHE_KEY, EXPECTED_QITAF_ERRORS)
from integrations.v1.gateway_clients.utils import format_verify_data
from integrations.v1.serializers.qitafpg_serializer import (
    QitafPaymentRequestSerializer
)
from payments.constants import (PAYMENT_STATUS_PAID,
                                PAYMENT_STATUS_DECLINED_RETRY,
                                PAYMENT_STATUS_PENDING, PAYMENT_METHOD_QITAF,
                                PAYMENT_METHOD_QITAFAND_CARD,
                                LANGUAGE_CODE_AR, PAYMENT_STATUS_DECLINED)
from payments.serializers.youpay_payments import (
    YouPayTransactionDataSerializer)
from services.v1.constants import (B2C_PAYBACK_YOUPAY_PRODUCT_CODE,
                                   B2C_PAYBACK_CONFIG_ENDPOINT)
from services.v1.views.common import add_payment_gateway_info_in_url
from services.v1.views.payment import PaymentRequestView
from services.v1.views.payment_handlers import PaymentHandlers

logger = logging.getLogger(__name__)


class QitafServiceManager(PaymentHandlers, PaymentRequestView):
    """
    Class to manage qitaf related operations
    """

    def __init__(self):
        self.qitaf_config = None
        self.transaction_id = None
        self.transaction_obj = None
        self.request_data = {}
        self.response_data = {}
        self.request_method = None
        self.request_type = None
        self.payment_status = None
        self.payment_method = None
        self.is_qitaf_enabled = None
        self.approved = False
        self.amount = None
        self.redeemed_point = None
        self.redeemed_amount = None
        self.redeemed_points = None
        self.payable_amount = None
        self.service_fee = None
        self.base_amount = None
        self.VAT_amount = None
        self.payment_gateway = PAYMENT_GATEWAY_B2CPAYBACK
        self.points_redeemed_mobile_number = None
        self.point_program = None
        self.point_collection_enabled = False
        self.brand_calculations = None

        self.class_name = "{}:".format(self.__class__.__name__)

    def get_configurations(self, amount, currency, transaction_id):
        product_code = B2C_PAYBACK_YOUPAY_PRODUCT_CODE
        amount = str(amount)
        currency = str(currency)
        if currency != CHECKOUT_SAUDI_CURRENCY:
            logger.info(
                "Skipping config api call to qitaf for non SAR "
                "transaction {}".format(transaction_id))
            return None
        else:
            config_request_data = {
                "amount": amount, "currency": currency,
                "product_code": product_code
            }
            request_data_json = json.dumps(config_request_data)
            gateway_obj = get_payment_gateway_config(QITAF_CACHE_KEY,
                                                     B2CPAYBACK_HUB_CODE)
            payback_domain = gateway_obj.domain
            try:
                url = payback_domain + B2C_PAYBACK_CONFIG_ENDPOINT

                response = requests.post(url, data=request_data_json,
                                         headers=QITAF_HEADERS)
                logger.info(
                    "config api call to qitaf for transaction {} "
                    "response {}".format(transaction_id, response.text))
                if response:
                    return response.json()
                else:
                    logger.error(
                        "No configuration received from qitaf configuration"
                        " api call to b2cpayback for transaction {}, response"
                        " {}".format(transaction_id, response.text))
                    return None
            except Exception as e:
                logger.error("config api call to b2cpayback failed",
                             exc_info=e)
                return None

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
            self.qitaf_config = get_config_from_payment_configurations(
                self.transaction_obj, PAYMENT_METHOD_QITAF)
            self.transaction_id = self.transaction_obj.transaction_id
            payload = self.get_qitaf_payment_data(request_data)
            qitaf_phone_number = request_data.get("mobile_number")

            data = {
                'transaction_id': str(self.transaction_id),
                'qitaf_phone_number': qitaf_phone_number,
            }

            payload.update(data)
            self.request_data = payload
            payload['MSISDN'] = payload.get('qitaf_phone_number')
            payload['apiclient'] = self.transaction_obj.api_client.name
            logger.info(
                "Youpay sending request data to qitaf generate otp api "
                "is {}".format(payload))
            url = self.qitaf_config.domain + QITAF_OTP_GENERATION_API
            headers = self.get_payment_header()

            response = requests.post(url, data=json.dumps(payload),
                                     headers=headers)
            logger.info("Response from Qitaf service {}".format(
                response.json()))
            if response:
                response_data = response.json()
                logger.info("qitaf payment response: {}".format(
                    response_data))
                self.response_data = response_data
                self.update_youpay_transaction_data({
                    'transaction_id': self.transaction_obj.transaction_id,
                    'payment_reference': response_data.get(
                        'payment_reference'),
                    'points_redeemed_mobile_number': qitaf_phone_number,
                    'qitaf_phone_number': qitaf_phone_number
                })

                return response_data, self.SUCCESS

            error_response = response.json()
            error_message = error_response.get('response_data', {}).get(
                'response_text', '')

            if error_message not in EXPECTED_QITAF_ERRORS:
                logger.error("Unexpected Qitaf error: {}".format(error_response))

            self.response_data = error_response

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
                request_type=PAYMENT_REQUEST_GENERATE_OTP,
            )

    def collect_points(self, data):
        """
        calls qitaf points collecting api
        """
        try:
            request_data = data

            self.transaction_obj = request_data.get('transaction_obj')
            self.qitaf_config = get_config_from_payment_configurations(
                self.transaction_obj, PAYMENT_METHOD_QITAF)
            self.transaction_id = str(self.transaction_obj.transaction_id)

            request_data.pop('transaction_obj')

            request_data['transaction_id'] = self.transaction_id
            request_data['invoice_id'] = self.transaction_obj.invoice_id
            request_data['customer_name'] = self.transaction_obj.customer_name
            request_data['customer_email'] = (
                self.transaction_obj.customer_email)
            request_data['apiclient'] = self.transaction_obj.api_client.name
            request_data['source_payment_method'] = (
                self.transaction_obj.payment_method)
            request_data['gateway_reference'] = (
                self.transaction_obj.payment_reference)
            request_data['currency'] = self.transaction_obj.currency
            request_data['language_code'] = self.transaction_obj.language
            request_data[
                'brand_calculations'] = self.transaction_obj.brand_calculations
            self.request_data = request_data
            logger.info(
                "Youpay sending request data to qitaf point collection api "
                "is {}".format(request_data))

            payload = json.dumps(request_data)

            url = self.qitaf_config.domain + QITAF_EARN_POINTS_API
            headers = self.get_payment_header()
            response = requests.post(url, data=payload, headers=headers)
            logger.info(
                "Response from qitaf point collection api for transaction {}"
                " is {}".format(self.transaction_id, response))
            if response:
                response_data = response.json()
                self.response_data = response_data
                logger.info(
                    "qitaf point collection api response for transaction {} :"
                    " {}".format(self.transaction_id, response_data))
                return response_data, self.SUCCESS

            logger.error(
                "Error in qitaf point collection api, {} for transaction "
                "{}".format(response.text, self.transaction_id))
            self.response_data = response.json()
            return {"error": response.text,
                    "partner_response": response.json()
                    }, self.QITAF_CONNECTION_ERROR

        except Exception as e:
            error = "Error in qitaf point collection api: {}".format(e)
            logger.error("Exception in qitaf point collection api: "
                         "{}".format(e), exc_info=True)
            return {"error": error}, self.QITAF_CONNECTION_ERROR
        finally:
            self.create_youpay_to_payment_gateways_data(
                transaction_obj=self.transaction_obj,
                transaction_id=self.transaction_id,
                request_data=json.dumps(self.request_data),
                response_data=json.dumps(self.response_data),
                request_method=REQUEST_METHOD_POST,
                request_type=PAYMENT_REQUEST_COLLECT_POINTS,
            )

    def prepare_redeem_payload(self, transaction_data):
        """
        prepares payload for qitaf redeem api
        """
        redeem_payload = {
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
            "channel_code": get_channel_code(self.transaction_obj),
        }
        return redeem_payload

    def redeem_points(self, data):
        """
        calls qitaf points redeem api
        """
        try:
            self.request_data = data
            self.transaction_obj = self.request_data.get('transaction_obj')
            self.qitaf_config = get_config_from_payment_configurations(
                self.transaction_obj, PAYMENT_METHOD_QITAF)
            self.transaction_id = self.transaction_obj.transaction_id
            payload = self.request_data
            language = self.transaction_obj.language

            serializer = YouPayTransactionDataSerializer(self.transaction_obj)
            transaction_data = serializer.data
            payload.update(self.prepare_redeem_payload(transaction_data))
            payload.pop('transaction_obj')
            source_payment_method = (
                PAYMENT_METHOD_QITAFAND_CARD if float(self.request_data.get(
                    'checkout_amount')) > 0 else PAYMENT_METHOD_QITAF)
            payload.update({"source_payment_method":source_payment_method})

            verify_response, verify_status = self.verify_transaction(
                transaction_data, payment_method=PAYMENT_METHOD_QITAF)
            if not verify_response:
                msg = (
                    "Youpay Qitaf transaction verification failed for"
                    " transaction id {} response is : {} ".format(
                        self.transaction_id, verify_response))
                logger.error(msg)
                return verify_response, self.CLIENT_TRANSACTION_VERIFICATION_FAILED

            is_verified = verify_response.get('is_verified', False)
            if not is_verified and verify_response:
                msg = (
                    "Youpay Qitaf transaction verification failed for"
                    " transaction id {} response is : {} ".format(
                        self.transaction_id, verify_response))
                logger.error(msg)
                self.response_data = verify_response
                return verify_response, self.CLIENT_TRANSACTION_VERIFICATION_FAILED

            url = self.qitaf_config.domain + QITAF_REDEEM_POINTS_API
            headers = self.get_payment_header()

            logger.info(
                "Youpay sending request data to qitaf redeem point api is {}"
                " headers {} ".format(payload, headers))

            response = requests.post(url, data=json.dumps(payload),
                                     headers=headers)

            if response:
                response_data = response.json()
                self.response_data = response_data
                logger.info("qitaf redeem point api response: {}".format(
                    response_data))
                response_data = self.handle_qitaf_response(
                    response_data, self.transaction_obj, self.request_data)
                return response_data, self.SUCCESS
            elif response.status_code == 400:
                response_data = response.json()
                self.response_data = response_data
                response_data = self.handle_qitaf_response(
                    response_data, self.transaction_obj, self.request_data)
                logger.info("qitaf redeem point api response: {} for {}"
                            "".format(response_data, self.transaction_id))
                return response_data, self.PAYMENT_FAILED
            elif response.status_code == 403:
                msg = "Qitaf Forbidden, or partial redemption not supported"
                logger.error("{}, {}".format(msg, response.text))
                return {"errors": msg}, self.QITAF_NOT_SUPPORTED
            else:
                logger.error("Error in qitaf redeem point api, {}"
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
                return {"errors": err_obj}, self.QITAF_CONNECTION_ERROR

        except Exception as e:
            error = "Exception in qitaf redeem point api: {}".format(e)
            logger.error("Exception in qitaf redeem point api: "
                         "{}".format(e), exc_info=True)
            return {"errors": error}, self.QITAF_CONNECTION_ERROR

        finally:
            if self.request_data.get("cvv"):
                self.request_data["cvv"] = "***"
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

    def qitaf_error_response_message(self, response_data):
        message = ""
        try:
            qitaf_error_msg = (response_data.get('response_text', "")
                               if self.transaction_obj.language == LANGUAGE_ENGLISH
                               else response_data.get('response_text_ar', ""))

            checkout_error_message = response_data.get(
                "checkout_response_data", {}).get(
                "response_summary", "")
            message = qitaf_error_msg if qitaf_error_msg else checkout_error_message
        except Exception as e:
            logger.error(
                "{} Exception occurred on {}, err {} ".format(
                    self.class_name, inspect.currentframe().f_code.co_name,
                    e))

        return message

    def handle_qitaf_response(self, response_data, payment_data,
                              request_data):
        message = "API request completed successfully"
        youpay_update_data = {}
        logger.info(
            "handle_qitaf_response data {}".format(response_data))
        is_success, is_redirect, redirect_url = False, False, None
        update_data = {}
        name_on_card = request_data.get("customer_name", "")

        is_full_redemption = response_data.get("is_full_redemption", False)
        if is_full_redemption is False:
            # Handle qitaf partial redemption response
            redirect_url = response_data.get('url')

            if redirect_url:
                is_success = True
                is_redirect = True
                self.payment_status = PAYMENT_STATUS_PENDING
                self.is_qitaf_enabled = True
                self.point_collection_enabled = (
                    auto_enable_or_disable_point_collection(
                        Q(
                            payment_method=PAYMENT_METHOD_QITAF, active=True,
                            earn_on_partial_redemption=True
                        ))
                )
                self.redeemed_amount = response_data.get('redeemed_amount')
                self.redeemed_point = response_data.get('redeemed_point')
                self.payable_amount = response_data.get('payable_amount')
                self.points_redeemed_mobile_number = response_data.get(
                    'redeemed_mobile_number')
                self.point_program = PAYMENT_METHOD_QITAF

            else:
                redirect_url = ('{}?transaction_id={}'.format(
                    payment_data.failure_url,
                    payment_data.transaction_id))
                is_success = False
                is_redirect = True
                message = self.qitaf_error_response_message(response_data)

                self.payment_status = PAYMENT_STATUS_DECLINED
        else:
            """Handle qiTaf full redemption response"""
            if str(response_data.get('response_code')) in ["0"]:
                '''Qitaf full redemption Success case'''
                self.payment_status = PAYMENT_STATUS_PAID
                self.approved = True
                paid_amount = response_data.get('amount')
                if paid_amount:
                    self.amount = paid_amount
                    update_data['amount'] = self.amount

                self.redeemed_amount = response_data.get('redeemed_amount')
                self.redeemed_point = response_data.get('redeemed_point')

                # on full redemption case
                self.payable_amount = 0
                self.service_fee = 0
                self.VAT_amount = 0

                self.points_redeemed_mobile_number = response_data.get(
                    'redeemed_mobile_number')
                self.point_program = PAYMENT_METHOD_QITAF

                redirect_url = ('{}?transaction_id={}'.format(
                    payment_data.success_url, payment_data.transaction_id))
                is_success, is_redirect = True, True
            else:
                '''Qitaf full redemption Failure case'''
                self.payment_status = PAYMENT_STATUS_DECLINED_RETRY
                is_redirect = False
                message = self.qitaf_error_response_message(response_data)

        self.payment_method = (
            PAYMENT_METHOD_QITAF if is_full_redemption
            else PAYMENT_METHOD_QITAFAND_CARD)

        youpay_update_data = {
            **update_data,
            **{
                "transaction_id": payment_data.transaction_id,
                "is_full_redemption": is_full_redemption,
                "payment_status": self.payment_status,
                "approved": self.approved,
                "payment_method": self.payment_method,
                "payment_gateway": self.payment_gateway,
                "redeemed_amount": self.redeemed_amount,
                "redeemed_points": self.redeemed_point,
                "amount": self.amount,
                "payable_amount": self.payable_amount,
                "service_fee": self.service_fee,
                "base_amount": self.base_amount,
                "VAT_amount": self.VAT_amount,
                "is_qitaf_enabled": self.is_qitaf_enabled,
                "point_collection_enabled": self.point_collection_enabled,
                "response_summary": response_data.get('reason'),
                "name_on_card": name_on_card,
                "points_redeemed_mobile_number": (
                    self.points_redeemed_mobile_number),
                "point_program": (
                    self.point_program),
                "brand_calculations": self.brand_calculations
            }
        }
        update_data.update(youpay_update_data)

        self.update_youpay_transaction_data(update_data)
        return_response = {
            "message": message if message else "Payment Failed",
            REDIRECT_URL: redirect_url,
            IS_REDIRECT: is_redirect,
            "qitaf_response": response_data,
            "is_success": is_success
        }
        return return_response

    def verification(self, request_data):
        """Qitaf Verification with b2c"""
        earned_point = None
        payment_scheme = None
        phone_number = None
        earn_reference = None
        points_collected_mobile_number = None

        request_transaction_id = request_data.get('transaction_id')
        logger.info(
            "Qitaf Verification with b2c started for transaction {}, data -->"
            " {}".format(request_transaction_id, request_data))

        if request_transaction_id:
            try:
                transaction_id = decrypt_string(request_transaction_id)
                transaction_obj = self.get_youpay_transaction_data(
                    transaction_id)

                formatted_data = format_verify_data(
                    request_data, transaction_obj)
                gateway_obj = get_config_from_payment_configurations(
                    self.transaction_obj, PAYMENT_METHOD_QITAF)

                qitaf_domain = gateway_obj.domain
                url = (qitaf_domain + QITAF_VERIFY_API +
                       "?&redemption_partner=QITAF")

                formatted_data.pop("transaction_id")
                response = requests.get(url, params=formatted_data,
                                        headers=QITAF_HEADERS)

                return_response_data = {}
                if response.status_code == status.HTTP_200_OK and (
                        response.json().get(
                            "status").lower() == PAYMENT_STATUS_PAID):
                    """Redemption verified successfully"""
                    logger.info(
                        "Qitaf Verification with b2c completed for "
                        "transaction {}".format(transaction_id))

                    response_data = response.json()
                    return_response_data["is_redirect"] = True
                    redirect_url = (transaction_obj.success_url +
                                    '?transaction_id=' + transaction_id)

                    return_response_data["redirect_url"] = redirect_url

                    approved = response_data.get("approved", False)
                    is_flagged = response_data.get("is_flagged", False)
                    is_gcc_card = response_data.get("is_gcc_card", False)
                    payment_status = PAYMENT_STATUS_PAID
                    return_response_data[IS_SUCCESS] = True
                    card_last4 = response_data.get("card_last4")
                    card_bin = response_data.get("card_bin")
                    card_issuer_country = response_data.get(
                        "card_issuer_country")
                    payment_scheme = response_data.get("payment_scheme")

                    self.handle_qitaf_collection(transaction_obj)
                else:
                    """Redemption failed"""
                    payment_status = PAYMENT_STATUS_DECLINED
                    return_response_data[IS_SUCCESS] = False
                    return_response_data['is_redirect'] = True
                    return_response_data['redirect_url'] = (
                            transaction_obj.failure_url +
                            '?transaction_id=' + transaction_id)
                    approved = False
                    is_flagged = False
                    is_gcc_card = False
                    card_last4 = ""
                    card_bin = ""
                    card_issuer_country = ""
                    response_data = response.json()
                    return_response_data["message"] = response_data.get(
                        "response_summary", "Payment Failed")

                return_response_data["payment_status"] = payment_status
                self.create_youpay_to_payment_gateways_data(
                    transaction_obj=transaction_obj,
                    transaction_id=transaction_obj.transaction_id,
                    request_data=json.dumps(formatted_data),
                    response_data=json.dumps(response_data),
                    request_method=REQUEST_METHOD_GET,
                    request_type=PAYMENT_REQUEST_VERIFY
                )

                from services.v1.api_clients.qitaf_service import (
                    get_calculated_youpay_transaction_data_with_qitaf_balance)

                """update youpay transaction data with qitaf balance 
                calculation on successfull payment"""
                calculated_youpay_transaction_data = (
                    get_calculated_youpay_transaction_data_with_qitaf_balance(
                        transaction_obj))

                update_data = {
                    'transaction_id': str(transaction_obj.transaction_id),
                    'payment_status': payment_status,
                    'is_flagged': is_flagged,
                    'approved': approved,
                    'is_gcc_card': is_gcc_card,
                    'earned_point': earned_point,
                    'card_last4': card_last4,
                    'card_bin': card_bin,
                    'card_issuer_country': card_issuer_country,
                    'payment_scheme': payment_scheme
                }
                update_data.update(calculated_youpay_transaction_data)

                logger.info("Qitaf Verification with b2c completed for "
                            "transaction {}, data to be updating {}".format(
                    transaction_id, update_data))
                self.update_youpay_transaction_data(update_data)
                return return_response_data, transaction_obj

            except Exception as e:
                logger.error(
                    "Verify api call to Qitaf failed for transaction {}"
                    "".format(request_transaction_id), exc_info=e)
                return None, None
        else:
            logger.error("Invalid transaction id ({}) received for Qitaf "
                         "verify api".format(request_transaction_id))
            return None, None

    def handle_qitaf_collection(self, transaction_obj):
        """
        Updating program, mobile number etc on Qitaf Verification
        """
        if transaction_obj.point_collection_enabled:
            if (transaction_obj.point_program != PAYMENT_METHOD_QITAF or
                    not transaction_obj.points_collected_mobile_number):
                transaction_obj.points_collected_mobile_number = (
                    transaction_obj.points_redeemed_mobile_number)
                transaction_obj.point_program = (
                    PAYMENT_METHOD_QITAF)
                transaction_obj.save()
