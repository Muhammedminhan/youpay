import copy
import json
import logging

import requests
from rest_framework import status

from core.constants import (REQUEST_METHOD_POST, PAYMENT_GATEWAY_B2CPAYBACK,
                            REQUEST_METHOD_GET)
from core.messages import (REDIRECT_URL, IS_REDIRECT, IS_SUCCESS,
                           GATEWAY_ERROR_OCCURRED)
from core.response_messages import YouPayResponse
from core.utils import (get_payment_gateway_config, get_app_config,
                        decrypt_string)
from integrations.common import update_brand_details, get_redemption_details
from integrations.constants import (
    B2CP_CACHE_KEY,
    B2CPAYBACK_HUB_CODE,
    NEQATY_POINT_BALANCE_API, PAYMENT_REQUEST_POINT_BALANCE,
    PAYMENT_REQUEST_GENERATE_OTP, NEQATY_OTP_GENERATION_API,
    NEQATY_REDEEM_POINTS_API, PAYMENT_REQUEST_REDEMPTION,
    NEQATY_CLIENT_CODE, CHECKOUTPG_PAYMENT_CONFIGURATIONS,
    CHECKOUT_SAUDI_CHANNEL_CODE, NEQATY_VERIFY_API, CONTENT_TYPE_HEADERS,
    PAYMENT_REQUEST_VERIFY, REDEMPTION_PARTNER_NEQATY,
    NEQATY_EARN_POINTS_API, PAYMENT_REQUEST_COLLECT_POINTS, )
from payments.constants import (PAYMENT_STATUS_PENDING, PAYMENT_METHOD_NEQATY,
                                LANGUAGE_CODE_AR,
                                PAYMENT_METHOD_NEQATY_AND_CARD,
                                PAYMENT_STATUS_PAID, PAYMENT_STATUS_DECLINED)
from payments.serializers.youpay_payments import (
    YouPayTransactionDataSerializer)
from services.v1.views.common import add_payment_gateway_info_in_url
from services.v1.views.payment import PaymentRequestView
from services.v1.views.payment_handlers import PaymentHandlers

logger = logging.getLogger(__name__)


class NeqatyServiceManager(PaymentHandlers, PaymentRequestView):
    """
    Class to manage Neqaty related operations
    """

    def __init__(self):
        self.neqaty_config = get_payment_gateway_config(B2CP_CACHE_KEY,
                                                        B2CPAYBACK_HUB_CODE)
        self.transaction_id = None
        self.transaction_obj = None
        self.request_data = {}
        self.response_data = {}
        self.request_method = None
        self.request_type = None
        self.payment_status = None
        self.payment_method = None
        self.point_collection_enabled = False
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

    def get_payment_header(self):
        """
        Returns headers
        """
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.neqaty_config.api_key,
            'X-API-KEY': self.neqaty_config.api_key
        }
        return headers

    def point_balance(self, data):
        """
        calls Neqaty points collecting api
        """
        try:
            request_data = data

            self.transaction_obj = request_data.get('transaction_obj')
            self.transaction_id = str(self.transaction_obj.transaction_id)
            language = self.transaction_obj.language

            is_updated, brand_details = update_brand_details(
                self.transaction_obj)
            if is_updated:
                brand_detail_items_set = brand_details.get("item_set", None)
                data.update({
                    "brand_details": brand_details})

                if not brand_detail_items_set or not len(
                        brand_detail_items_set) or not is_updated:
                    logger.error("Brand details not found for transaction {}"
                                 "".format(self.transaction_id))
                    return None, self.BRAND_DETAILS_MISSING

            request_data.pop('transaction_obj')

            logger.info(
                "Youpay sending request data to Neqaty point balance api "
                "is {} for transaction {}".format(request_data,
                                                  self.transaction_id))

            self.request_data = request_data

            payload = json.dumps(request_data)

            url = self.neqaty_config.domain + NEQATY_POINT_BALANCE_API
            headers = self.get_payment_header()
            response = requests.post(url, data=payload, headers=headers)
            logger.info("Response from Neqaty point balance api {}"
                        "".format(response))
            if response:
                response_data = response.json()
                self.response_data = response_data
                logger.info("Neqaty point balance api response: {}".format(
                    response_data))
                formatted_response = (
                    self.format_point_balance_response(response_data))

                self.update_youpay_transaction_data({
                    'transaction_id': self.transaction_obj.transaction_id,
                    'payment_reference': response_data.get(
                        'partner_response').get('reference_id'),
                    'brand_calculations':
                        response_data.get('partner_response').get(
                            'redeem_options'),
                    'payment_status': PAYMENT_STATUS_PENDING,
                    'points_redeemed_mobile_number': self.request_data.get(
                        'msisdn'),
                    'payment_gateway': PAYMENT_GATEWAY_B2CPAYBACK,
                    'payment_method': PAYMENT_METHOD_NEQATY,
                    'available_points': response_data.get(
                        "partner_response").get("available_points"),
                    "brand_details": brand_details
                })
                return formatted_response, self.SUCCESS

            elif hasattr(response, 'text'):
                self.response_data = json.loads(response.text)
                logger.error("Error in Neqaty point balance api, {}"
                             "".format(response.text))
                partner_response = self.response_data.get(
                    "partner_response")
                self.update_youpay_transaction_data({
                    'transaction_id': self.transaction_obj.transaction_id,
                    'payment_reference': self.response_data.get(
                        'reference_id'),
                    'payment_status': PAYMENT_STATUS_PENDING,
                    'payment_gateway': PAYMENT_GATEWAY_B2CPAYBACK,
                    'payment_method': PAYMENT_METHOD_NEQATY,
                    "brand_details": brand_details
                })
                if language == LANGUAGE_CODE_AR:
                    message = partner_response.get("response_text_ar")
                else:
                    message = partner_response.get("response_text")

                err_obj = {
                    "message": message,
                    "code": self.response_data.get("code")
                }
                return {"errors": err_obj}, self.NEQATY_CONNECTION_ERROR
            else:
                logger.error(
                    "unable to get response from b2c_payback-neqaty for "
                    "point balance")
                err_obj = {
                    "message": GATEWAY_ERROR_OCCURRED,
                }
                return {"errors": err_obj}, self.NEQATY_CONNECTION_ERROR

        except Exception as e:
            error = "Error in Neqaty point balance api: {}".format(e)
            logger.error("Exception in Neqaty point balance api: "
                         "{}".format(e), exc_info=True)
            return {"error": error}, self.NEQATY_CONNECTION_ERROR
        finally:
            self.create_youpay_to_payment_gateways_data(
                transaction_obj=self.transaction_obj,
                transaction_id=self.transaction_id,
                request_data=json.dumps(self.request_data),
                response_data=json.dumps(self.response_data),
                request_method=REQUEST_METHOD_POST,
                request_type=PAYMENT_REQUEST_POINT_BALANCE,
            )

    def generate_otp(self, data):
        """
        calls neqaty otp generating api and returns otp
        """
        try:
            self.transaction_obj = data.get('transaction_obj')
            self.transaction_id = self.transaction_obj.transaction_id
            redeem_code = data.get('redeem_code')
            data.pop('transaction_obj')
            brand_calculations = self.transaction_obj.brand_calculations
            updated_brand_calculations = self.update_brand_calculations(
                brand_calculations, redeem_code)
            self.request_data = data

            redemption_details = {
                "redeemed_points": updated_brand_calculations.get(
                    "redeemPoints"),
                "redeemed_amount": updated_brand_calculations.get(
                    "redeemAmount"),
                "payable_amount": updated_brand_calculations.get(
                    "sum_card_payment_amount")
            }
            data.update(redemption_details)

            logger.info(
                "Youpay sending request data to neqaty generate otp api "
                "is {}".format(data))
            url = self.neqaty_config.domain + NEQATY_OTP_GENERATION_API
            headers = self.get_payment_header()

            response = requests.post(url, data=json.dumps(data),
                                     headers=headers)
            logger.info("Response from neqaty service {}".format(response))
            if response:
                response_data = response.json()
                logger.info("neqaty payment response: {}".format(
                    response_data))
                self.response_data = response_data

                updated_dict = {
                    'transaction_id': self.transaction_obj.transaction_id,
                    'brand_calculations': updated_brand_calculations
                }
                redemption_details = get_redemption_details(
                    self.transaction_obj, updated_brand_calculations)
                updated_dict.update(redemption_details)
                self.update_youpay_transaction_data(updated_dict)
                return response_data, self.SUCCESS

            logger.error("Error in neqaty otp, {}".format(response.json()))
            self.response_data = response.json()

            return ({"error": response.json()},
                    self.NEQATY_CONNECTION_ERROR)

        except Exception as e:
            error = "Exception in neqaty generate otp api: {}".format(e)
            logger.error(error, exc_info=True)
            self.response_data = {}
            return {"error": error}, self.NEQATY_CONNECTION_ERROR
        finally:
            self.create_youpay_to_payment_gateways_data(
                transaction_obj=self.transaction_obj,
                transaction_id=self.transaction_id,
                request_data=json.dumps(self.request_data),
                response_data=json.dumps(self.response_data),
                request_method=REQUEST_METHOD_POST,
                request_type=PAYMENT_REQUEST_GENERATE_OTP,
            )

    def redeem_points(self, data):
        """
        calls neqaty points redeem api
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

            verify_response, verify_status = self.verify_transaction(
                transaction_data,
                payment_method=self.transaction_obj.payment_method)
            is_verified = verify_response.get('is_verified', False)

            if verify_status == status.HTTP_200_OK and is_verified:
                url = self.neqaty_config.domain + NEQATY_REDEEM_POINTS_API
                headers = self.get_payment_header()

                logger.info(
                    "Youpay sending request data to neqaty redeem point api "
                    "is {} headers {} ".format(payload, headers))

                response = requests.post(url, data=json.dumps(payload),
                                         headers=headers)
                response_data, code = self.handle_neqaty_point_redeem_response(
                    response,
                    self.transaction_obj, self.request_data)
                return response_data, code

            else:
                msg = (
                    "Youpay neqaty transaction verification failed for"
                    " transaction id {} response is : {} ".format(
                        self.transaction_id, verify_response))
                logger.error(msg)
                self.response_data = verify_response
                return verify_response, self.CLIENT_TRANSACTION_VERIFICATION_FAILED

        except Exception as e:
            error = "Exception in neqaty redeem point api: {}".format(e)
            logger.error("Exception in neqaty redeem point api: "
                         "{}".format(e), exc_info=True)
            return {"errors": error}, self.NEQATY_CONNECTION_ERROR

        finally:
            self.create_youpay_to_payment_gateways_data(
                transaction_obj=self.transaction_obj,
                transaction_id=self.transaction_id,
                request_data=json.dumps(self.request_data),
                response_data=json.dumps(self.response_data),
                request_method=REQUEST_METHOD_POST,
                request_type=PAYMENT_REQUEST_REDEMPTION,
            )

    def format_point_balance_response(self, data):
        redeem_options = copy.deepcopy(
            data.get("partner_response").get("redeem_options"))
        options = redeem_options
        code = data.get("code")
        message = data.get("message")
        available_points = data.get("partner_response").get("point_balance")
        reference_id = data.get("partner_response").get("reference_id")

        for option in options:
            option.pop('calculated_item_details')

        formatted_data = {
            "code": code,
            "message": message,
            "redeem_options": options,
            "available_points": available_points,
            "reference_id": reference_id
        }
        return formatted_data

    def prepare_redeem_payload(self, transaction_data):
        """
        prepares payload for neqaty redeem api
        """
        redeem_payload = {
            "response_url": add_payment_gateway_info_in_url(
                transaction_data=transaction_data,
                app_config=get_app_config(),
                params=('?id=' + self.request_data.get("encrypted_id") +
                        "&redemption_reference_id=" + transaction_data.get(
                            "payment_reference") + "&redemption_partner=" +
                        REDEMPTION_PARTNER_NEQATY),
                code=NEQATY_CLIENT_CODE,
            ),
            "invoice_id": self.transaction_obj.invoice_id,
            "brand_calculations": self.transaction_obj.brand_calculations,
            "customer_ip_address": self.transaction_obj.ip,
            "channel_code": CHECKOUTPG_PAYMENT_CONFIGURATIONS.get(
                transaction_data.get("currency").upper()),
        }
        return redeem_payload

    def handle_neqaty_response(self, response_data, payment_data,
                               request_data):
        youpay_update_data = {}
        logger.info(
            "handle_neqaty_response data {}".format(response_data))
        is_success, is_redirect, redirect_url = False, False, None
        update_data = {}

        is_full_redemption = response_data.get("partner_response").get(
            "is_full_redemption", False)
        redemption_status = response_data.get("partner_response").get(
            "redemption_status", False)
        name_on_card = ""
        message = self.SUCCESS
        amount = payment_data.amount

        if redemption_status:
            if is_full_redemption is False:
                redirect_url = response_data.get('partner_response',
                                                 {}).get('url')
                if redirect_url:
                    is_success = True
                    is_redirect = True
                    self.payment_status = PAYMENT_STATUS_PENDING
                    amount = payment_data.brand_calculations.get(
                        'sum_net_amount', None)
                    name_on_card = request_data.get("customer_name")
                    self.point_collection_enabled = True

                else:
                    redirect_url = ('{}?transaction_id={}'.format(
                        payment_data.failure_url,
                        payment_data.transaction_id))
                    is_success = False
                    is_redirect = True
                    message = response_data.get("partner_response").get(
                        "checkout_response_data", {}).get("response_summary",
                                                          "Payment Failed")
                    self.payment_status = PAYMENT_STATUS_DECLINED

            else:
                '''Neqaty full redemption Success case'''
                self.payment_status = PAYMENT_STATUS_PAID
                self.approved = True
                amount = payment_data.brand_calculations.get(
                    'sum_net_amount', None)

                redirect_url = ('{}?transaction_id={}'.format(
                    payment_data.success_url,
                    payment_data.transaction_id))
                is_success, is_redirect = True, True

        self.payment_method = (
            PAYMENT_METHOD_NEQATY if is_full_redemption
            else PAYMENT_METHOD_NEQATY_AND_CARD)

        youpay_update_data = {
            **update_data,
            **{
                "transaction_id": payment_data.transaction_id,
                "amount": amount,
                "is_full_redemption": is_full_redemption,
                "payment_status": self.payment_status,
                "approved": self.approved,
                "response_summary": response_data.get(
                    'reason'),
                "payment_method": self.payment_method,
                "name_on_card": name_on_card,
                "point_collection_enabled": self.point_collection_enabled,
            }
        }
        update_data.update(youpay_update_data)

        self.update_youpay_transaction_data(update_data)
        return_response = {
            "message": message,
            REDIRECT_URL: redirect_url,
            IS_REDIRECT: is_redirect,
            "is_success": is_success
        }
        return return_response

    def handle_neqaty_point_redeem_response(self, response, transaction_obj,
                                            request_data):
        if response:
            response_data = response.json()
            self.response_data = response_data
            logger.info("Neqaty redeem point api response: {}".format(
                response_data))

            response_data = self.handle_neqaty_response(
                response_data, self.transaction_obj, request_data)
            return response_data, self.SUCCESS
        elif response.status_code == status.HTTP_403_FORBIDDEN:
            msg = "Neqaty Forbidden, or partial redemption not supported"
            logger.error("{}, {}".format(msg, response.text))
            return {"errors": msg}, self.NEQATY_NOT_SUPPORTED
        else:
            logger.error("Error in neqaty redeem point api, {}"
                         "".format(response.text))
            if hasattr(response, 'text'):
                self.response_data = json.loads(response.text)

                partner_response = self.response_data.get(
                    "partner_response")

                redemption_status = partner_response.get(
                    'redemption_status', False)

                if redemption_status:
                    response_data = self.handle_neqaty_response(
                        self.response_data, self.transaction_obj,
                        request_data)
                    return response_data, self.PAYMENT_FAILED
                else:
                    partner_response = self.response_data.get(
                        "partner_response")
                    language = transaction_obj.language
                    if language == LANGUAGE_CODE_AR:
                        message = partner_response.get("response_text_ar")
                    else:
                        message = partner_response.get("response_text")

                    err_obj = {
                        "message": message,
                        "code": self.response_data.get("code"),
                        "is_full_redemption": self.response_data.get(
                            "is_full_redemption")
                    }
                    return {
                        "errors": err_obj}, self.NEQATY_CONNECTION_ERROR
            else:
                msg = "unable to get response from b2c_payback-neqaty"
                logger.error(msg)
                return {"errors": msg}, self.NEQATY_CONNECTION_ERROR

    def update_brand_calculations(self, data, redeem_code):
        if data:
            for item in data:
                if item["redeemCode"] == redeem_code:
                    return item
        return None

    def verification(self, request_data):
        """Neqaty Verification with b2c"""
        earn_reference = None

        request_transaction_id = request_data.get('transaction_id')
        logger.info(
            "Neqaty Verification with b2c started for transaction {}, data -->"
            " {}".format(request_transaction_id, request_data))

        if request_transaction_id:
            try:
                transaction_id = decrypt_string(request_transaction_id)
                transaction_obj = self.get_youpay_transaction_data(
                    transaction_id)

                request_data['invoice_id'] = transaction_obj.invoice_id
                request_data['channel_code'] = CHECKOUT_SAUDI_CHANNEL_CODE

                gateway_obj = get_payment_gateway_config(
                    B2CP_CACHE_KEY, B2CPAYBACK_HUB_CODE)

                neqaty_domain = gateway_obj.domain
                url = (neqaty_domain + NEQATY_VERIFY_API +
                       "?&redemption_partner=NEQATY")

                request_data.pop("transaction_id")
                response = requests.get(url, params=request_data,
                                        headers=CONTENT_TYPE_HEADERS)

                return_response_data = {}
                if response.status_code == status.HTTP_200_OK and (
                        response.json().get(
                            "status").lower() == PAYMENT_STATUS_PAID):
                    """Redemption verified successfully"""
                    logger.info(
                        "Neqaty Verification with b2c completed for "
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
                    self.handle_neqaty_collection(transaction_obj)
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
                    response_data = response.json()
                    card_last4 = response_data.get("card_last4", "")
                    card_bin = response_data.get("card_bin", "")
                    card_issuer_country = response_data.get(
                        "card_issuer_country", "")
                    return_response_data['message'] = response_data.get(
                        "response_summary", "")

                return_response_data["payment_status"] = payment_status
                self.create_youpay_to_payment_gateways_data(
                    transaction_obj=transaction_obj,
                    transaction_id=transaction_obj.transaction_id,
                    request_data=json.dumps(request_data),
                    response_data=json.dumps(response_data),
                    request_method=REQUEST_METHOD_GET,
                    request_type=PAYMENT_REQUEST_VERIFY
                )

                update_data = {
                    'transaction_id': str(transaction_obj.transaction_id),
                    'payment_status': payment_status,
                    'is_flagged': is_flagged,
                    'approved': approved,
                    'is_gcc_card': is_gcc_card,
                    'card_last4': card_last4,
                    'card_bin': card_bin,
                    'card_issuer_country': card_issuer_country
                }

                logger.info("Neqaty Verification with b2c completed for "
                            "transaction {}, data to be updating {}".format(
                    transaction_id, update_data))
                self.update_youpay_transaction_data(update_data)
                return return_response_data, transaction_obj

            except Exception as e:
                logger.error(
                    "Verify api call to Neqaty failed for transaction {}"
                    "".format(request_transaction_id), exc_info=e)
                return None, None
        else:
            logger.error("Invalid transaction id ({}) received for Neqaty "
                         "verify api".format(request_transaction_id))
            return None, None

    def update_points_collected_mobile_number(self, data):
        """
        To update neqaty phone number
        """
        try:
            return self.update_youpay_transaction_data(data)
        except Exception as e:
            error = ("Exception in updating points_collected_mobile_number "
                     "for Neqaty: {}").format(e)
            logger.error(error)
            return False

    def collect_points(self, transaction_obj):
        """
        calls neqaty points collecting api
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
                return None, response_obj.NEQATY_ALREADY_COLLECTED

            if transaction_obj.payment_method in [
                PAYMENT_METHOD_NEQATY_AND_CARD
            ]:
                paid_amount = transaction_obj.payable_amount
            else:
                paid_amount = transaction_obj.amount

            request_data = {
                "mobile_number": transaction_obj.points_collected_mobile_number,
                "customer_email": transaction_obj.customer_email,
                "customer_name": transaction_obj.customer_name,
                "invoice_id": transaction_obj.invoice_id,
                "gateway_reference": transaction_obj.payment_reference,
                "currency": transaction_obj.currency,
                "client_code": NEQATY_CLIENT_CODE,
                "amount": str(paid_amount),
                "platform": transaction_obj.platform,

                "item_details_list": transaction_obj.brand_details.get(
                    "item_set", None),
                "brand_calculations": transaction_obj.brand_calculations,
                "language_code": transaction_obj.language,
                "redeemed_amount": (
                    str(transaction_obj.redeemed_amount) if
                    transaction_obj.redeemed_amount else 0),
            }

            self.transaction_obj = transaction_obj
            self.transaction_id = str(self.transaction_obj.transaction_id)

            logger.info(
                "Youpay sending request data to neqaty point collection api "
                "is {}".format(request_data))

            request_data['transaction_id'] = "youpay|" + self.transaction_id
            self.request_data = request_data

            payload = json.dumps(request_data)

            url = self.neqaty_config.domain + NEQATY_EARN_POINTS_API
            headers = self.get_payment_header()
            response = requests.post(url, data=payload, headers=headers)
            logger.info("Response from neqaty point collection api {}"
                        "".format(response))
            if response:
                response_data = response.json()
                self.response_data = response_data
                logger.info("neqaty point collection api response: {}".format(
                    response_data))
                return response_data, self.SUCCESS
            elif hasattr(response, 'text'):
                self.response_data = json.loads(response.text)
                logger.error("Error in neqaty point collection api, {}"
                             "".format(response.text))
                self.response_data = response.json()
                return {"error": response.text}, self.NEQATY_CONNECTION_ERROR
            else:
                msg = ("unable to get response from b2c_payback-neqaty for "
                       "point collection")
                logger.error(msg)
                return {"errors": msg}, self.NEQATY_CONNECTION_ERROR

        except Exception as e:
            logger.error("Exception in neqaty point collection api: "
                         "{}".format(e), exc_info=True)
            return None, self.NEQATY_CONNECTION_ERROR
        finally:
            self.create_youpay_to_payment_gateways_data(
                transaction_obj=self.transaction_obj,
                transaction_id=self.transaction_id,
                request_data=json.dumps(self.request_data),
                response_data=json.dumps(self.response_data),
                request_method=REQUEST_METHOD_POST,
                request_type=PAYMENT_REQUEST_COLLECT_POINTS,
            )

    def handle_neqaty_collection(self, transaction_obj):
        if transaction_obj.point_collection_enabled:
            """If point collection enabled"""
            if transaction_obj.points_collection_enabled_program != (
                    PAYMENT_METHOD_NEQATY):
                transaction_obj.points_collected_mobile_number = (
                    transaction_obj.points_redeemed_mobile_number)
                transaction_obj.points_collection_enabled_program = (
                    PAYMENT_METHOD_NEQATY)
                transaction_obj.save()
