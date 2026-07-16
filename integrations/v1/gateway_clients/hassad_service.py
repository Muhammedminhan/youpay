import inspect
import json
import logging

import requests
from django.db.models import Q
from rest_framework import status

from core.constants import (REQUEST_METHOD_POST, PAYMENT_GATEWAY_B2CPAYBACK,
                            REQUEST_METHOD_GET)
from core.messages import REDIRECT_URL, IS_REDIRECT, IS_SUCCESS
from core.response_messages import YouPayResponse
from core.utils import (get_app_config,
                        auto_enable_or_disable_point_collection,
                        decrypt_string, get_channel_code,
                        get_config_from_payment_configurations)
from integrations.constants import (
    PAYMENT_REQUEST_COLLECT_POINTS,
    B2CP_EARN_POINTS_API,
    PAYMENT_REQUEST_GENERATE_OTP, B2CP_OTP_GENERATION_API,
    B2CP_REDEEM_POINTS_API, PAYMENT_REQUEST_REDEMPTION,
    B2CP_VERIFY_API,
    PAYMENT_REQUEST_VERIFY,
    PAYMENT_DECLINED_STATUS, HASSAD_CLIENT_CODE, HASSAD_NOT_ACCEPTED_CODE)
from integrations.v1.gateway_clients.utils import format_verify_data
from integrations.v1.serializers.hassad_serializer import (
    HassadPaymentRequestSerializer)
from payments.constants import (PAYMENT_METHOD_HASSAD, LANGUAGE_CODE_AR,
                                PAYMENT_STATUS_PAID,
                                PAYMENT_STATUS_DECLINED_RETRY,
                                PAYMENT_METHOD_HASSAD_AND_CARD,
                                PAYMENT_STATUS_PENDING,
                                PAYMENT_STATUS_DECLINED)
from payments.serializers.youpay_payments import (
    YouPayTransactionDataSerializer)
from services.v1.views.common import add_payment_gateway_info_in_url
from services.v1.views.payment import PaymentRequestView
from services.v1.views.payment_handlers import PaymentHandlers

logger = logging.getLogger(__name__)


class HassadServiceManager(PaymentHandlers, PaymentRequestView):
    """
    Class to manage Hassad related operations
    """

    def __init__(self):
        self.hassad_config = None
        self.transaction_id = None
        self.transaction_obj = None
        self.request_data = {}
        self.response_data = {}
        self.request_method = None
        self.request_type = None
        self.payment_status = None
        self.payment_method = None
        self.approved = False
        self.amount = None
        self.redeemed_point = None
        self.redeemed_amount = None
        self.payable_amount = None
        self.service_fee = None
        self.base_amount = None
        self.VAT_amount = None
        self.payment_gateway = PAYMENT_GATEWAY_B2CPAYBACK
        self.points_redeemed_mobile_number = None
        self.point_program = None
        self.point_collection_enabled = False
        self.brand_calculations = None

    def get_payment_header(self):
        """
        Returns header
        """
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.hassad_config.api_key,
            'X-API-KEY': self.hassad_config.api_key
        }
        return headers

    def update_points_collected_mobile_number(self, data):
        """
        To update Hassad phone number
        """
        try:
            return self.update_youpay_transaction_data(data)
        except Exception as e:
            error = ("Exception in updating points_collected_mobile_number "
                     "for hassad: {}").format(e)
            logger.error(error)
            return False

    @staticmethod
    def get_hassad_payment_data(data):
        """
        returns data to be passed to b2c_payback
        """
        if data.get('transaction_obj'):
            payment_data = HassadPaymentRequestSerializer(data)
            return payment_data.data
        else:
            logger.error("transaction_data or request_data is not available")
            return None

    def generate_otp(self, data):
        """
        calls Hassad otp generating api and returns otp

        Args:
            data (dict): Data for generating otp request.
        Returns:
            Tuple containing status code and response data.
        """
        try:
            request_data = data['request_data']
            self.transaction_obj = request_data.get('transaction_obj')
            self.hassad_config = get_config_from_payment_configurations(
                self.transaction_obj, PAYMENT_METHOD_HASSAD)
            logger.info("Hassad config is {}".format(self.hassad_config))

            self.transaction_id = self.transaction_obj.transaction_id
            payload = self.get_hassad_payment_data(request_data)
            hassad_phone_number = request_data.get("mobile_number")

            data = {
                'transaction_id': str(self.transaction_id),
                'hassad_phone_number': hassad_phone_number,
                'source_payment_method': PAYMENT_METHOD_HASSAD
            }

            payload.update(data)
            self.request_data = payload
            payload['apiclient'] = self.transaction_obj.api_client.name
            payload['client_code'] = HASSAD_CLIENT_CODE

            url = self.hassad_config.domain + B2CP_OTP_GENERATION_API
            headers = self.get_payment_header()
            logger.info(
                "Youpay sending request data to Hassad generate otp api {}"
                "is {} for transaction id {} with header {}".format(
                    url, payload, self.transaction_id, headers))
            response = requests.post(url, data=json.dumps(payload),
                                     headers=headers)

            if response.status_code == status.HTTP_200_OK:
                response_data = response.json()
                logger.info("Hassad payment response: {} for transaction id {}"
                            .format(response_data, self.transaction_id))
                self.response_data = response_data.get("partner_response")
                self.update_youpay_transaction_data({
                    'transaction_id': self.transaction_obj.transaction_id,
                    'payment_reference': self.response_data.get(
                        'payment_reference'),
                    'points_redeemed_mobile_number': hassad_phone_number,
                })
                return response_data, self.SUCCESS

            try:
                response_data = response.json()
            except ValueError:
                response_data = {"response": response.text}

            self.response_data = response_data
            error_code = self.response_data.get('code')
            if error_code == HASSAD_NOT_ACCEPTED_CODE:
                logger.info("OTP generation rejected error in Hassad, {}"
                            .format(self.response_data))
                return {"error": response.json()}, self.HASSAD_TRY_AFTER_SOMETIME

            logger.error("Error in Hassad otp, {} for transaction id "
                "{}".format(self.response_data, self.transaction_id))
            return {"error": response_data}, response_data.get("code")
        except Exception as e:
            error = ("Exception in Hassad generate otp api: {} for "
                     "transaction id {}").format(e, self.transaction_id)
            logger.error(error, exc_info=True)
            self.response_data = {}
            return {"error": error}, self.HASSAD_CONNECTION_ERROR
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
        calls hassad points collecting api
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
                return None, response_obj.HASSAD_ALREADY_COLLECTED

            if transaction_obj.payment_method in [
                PAYMENT_METHOD_HASSAD, PAYMENT_METHOD_HASSAD_AND_CARD
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
                "client_code": HASSAD_CLIENT_CODE,
                "amount": str(paid_amount),
                "platform": transaction_obj.platform,
                "item_details_list": transaction_obj.brand_details.get(
                    "item_set", None),
                "brand_calculations": transaction_obj.brand_calculations,
                "language_code": transaction_obj.language,
                "redeemed_amount": (
                    str(transaction_obj.redeemed_amount) if
                    transaction_obj.redeemed_amount else 0),
                "apiclient": transaction_obj.api_client.name,
                "source_payment_method": transaction_obj.payment_method
            }

            self.transaction_obj = transaction_obj
            self.hassad_config = get_config_from_payment_configurations(
                self.transaction_obj, PAYMENT_METHOD_HASSAD)
            self.transaction_id = str(self.transaction_obj.transaction_id)

            logger.info(
                "Youpay sending request data to hassad point collection api "
                "is {}".format(request_data))

            request_data['transaction_id'] = self.transaction_id
            self.request_data = request_data

            payload = json.dumps(request_data)

            url = self.hassad_config.domain + B2CP_EARN_POINTS_API
            headers = self.get_payment_header()
            response = requests.post(url, data=payload, headers=headers)
            logger.info("Response from hassad point collection api {}"
                        "".format(response))
            if response.status_code == status.HTTP_200_OK:
                response_data = response.json()
                self.response_data = response_data
                logger.info("hassad point collection api response: {}".format(
                    response_data))
                return response_data, self.SUCCESS
            elif hasattr(response, 'text'):
                self.response_data = json.loads(response.text)
                logger.error("Error in hassad point collection api, {}"
                             "".format(response.text))
                self.response_data = response.json()
                return {"error": response.text,
                        "partner_response": response.json()
                        }, self.HASSAD_CONNECTION_ERROR
            else:
                msg = ("unable to get response from b2c_payback-hassad for "
                       "point collection")
                logger.error(msg)
                return {"errors": msg}, self.HASSAD_CONNECTION_ERROR

        except Exception as e:
            logger.error("Exception in hassad point collection api: "
                         "{}".format(e), exc_info=True)
            return None, self.HASSAD_CONNECTION_ERROR
        finally:
            self.create_youpay_to_payment_gateways_data(
                transaction_obj=self.transaction_obj,
                transaction_id=self.transaction_id,
                request_data=json.dumps(self.request_data),
                response_data=json.dumps(self.response_data),
                request_method=REQUEST_METHOD_POST,
                request_type=PAYMENT_REQUEST_COLLECT_POINTS,
            )

    def verification(self, request_data):
        """
        Hassad verification with b2c

        Args:
            request_data (dict):  Contains transaction details.
        Returns:
            return_response_data: Processed response.
            transaction_obj (obj): Payment transaction object.
        """
        earned_point = None
        payment_scheme = None

        request_transaction_id = request_data.get('transaction_id')
        logger.info(
            "Hassad Verification with b2c started for transaction {},"
            " data --> {}".format(request_transaction_id, request_data))

        if request_transaction_id:
            try:
                transaction_id = decrypt_string(request_transaction_id)
                transaction_obj = self.get_youpay_transaction_data(
                    transaction_id)

                formatted_data = format_verify_data(
                    request_data, transaction_obj)
                gateway_obj = get_config_from_payment_configurations(
                    transaction_obj, PAYMENT_METHOD_HASSAD)

                hassad_domain = gateway_obj.domain
                url = (hassad_domain + B2CP_VERIFY_API +
                       "?&redemption_partner=HASSAD")
                headers = {'Content-Type': 'application/json'}
                formatted_data.pop("transaction_id")
                response = requests.get(url, params=formatted_data,
                                        headers=headers)

                return_response_data = {}
                if (response.status_code == status.HTTP_200_OK and
                    (response.json().get("status") or "").lower() ==
                        PAYMENT_STATUS_PAID):
                    """Redemption verified successfully"""
                    logger.info(
                        "Hassad Verification with b2c completed for "
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

                    self.handle_hassad_collection(transaction_obj)
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

                from services.v1.api_clients.hassad_service import (
                get_calculated_youpay_transaction_data_with_hassad_balance)

                """update youpay transaction data with Hassad balance 
                calculation on successfull payment"""
                calculated_youpay_transaction_data = (
                    get_calculated_youpay_transaction_data_with_hassad_balance(
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

                logger.info("Hassad Verification with b2c completed for "
                            "transaction {}, data to be updating {}".format(
                                transaction_id, update_data))
                self.update_youpay_transaction_data(update_data)
                return return_response_data, transaction_obj

            except Exception as e:
                logger.error(
                    "Verify api call to Hassad failed for transaction {}"
                    .format(request_transaction_id), exc_info=e)
                return None, None
        else:
            logger.error("Invalid transaction id ({}) received for Hassad "
                         "verify api".format(request_transaction_id))
            return None, None

    def redeem_points(self, data):
        """
        calls hassad points redeem api
        """
        try:
            self.request_data = data
            self.transaction_obj = self.request_data.get('transaction_obj')
            self.hassad_config = get_config_from_payment_configurations(
                self.transaction_obj, PAYMENT_METHOD_HASSAD)
            self.transaction_id = self.transaction_obj.transaction_id
            payload = self.request_data

            serializer = YouPayTransactionDataSerializer(self.transaction_obj)
            transaction_data = serializer.data
            payload.update(self.prepare_redeem_payload(transaction_data))
            payload.pop('transaction_obj')
            self.payment_method = (PAYMENT_METHOD_HASSAD_AND_CARD
                                   if float(self.request_data.get(
                                        'checkout_amount')) > 0 else
                                   PAYMENT_METHOD_HASSAD)
            payload.update({"source_payment_method": self.payment_method})

            verify_response, verify_status = self.verify_transaction(
                transaction_data, payment_method=PAYMENT_METHOD_HASSAD)
            if not verify_response:
                msg = (
                    "Youpay Hassad transaction verification failed for"
                    " transaction id {} response is : {} ".format(
                        self.transaction_id, verify_response))
                logger.error(msg)
                return (verify_response,
                        self.CLIENT_TRANSACTION_VERIFICATION_FAILED)

            is_verified = verify_response.get('is_verified', False)
            if not is_verified and verify_response:
                msg = (
                    "Youpay Hassad transaction verification failed for"
                    " transaction id {} response is : {} ".format(
                        self.transaction_id, verify_response))
                logger.error(msg)
                self.response_data = verify_response
                return (verify_response,
                        self.CLIENT_TRANSACTION_VERIFICATION_FAILED)

            url = self.hassad_config.domain + B2CP_REDEEM_POINTS_API
            headers = self.get_payment_header()

            logger.info(
                "Youpay sending request data to hassad redeem point api is {}"
                " headers {} ".format(payload, headers))

            response = requests.post(url, data=json.dumps(payload),
                                     headers=headers)

            if response.status_code == status.HTTP_200_OK:
                response_data = response.json()
                self.response_data = response_data
                logger.info("hassad redeem point api response: {}".format(
                    response_data))
                response_data = self.handle_hassad_response(
                    response_data, self.transaction_obj)
                return response_data, self.SUCCESS
            elif response.status_code == 400:
                response_data = response.json()
                self.response_data = response_data
                response_data = self.handle_hassad_response(
                    response_data, self.transaction_obj)
                logger.info("Hassad redeem point api response: {} for {}"
                            "".format(response_data, self.transaction_id))
                return response_data, self.PAYMENT_FAILED
            elif response.status_code == 403:
                msg = "Hassad Forbidden, or partial redemption not supported"
                logger.error("{}, {}".format(msg, response.text))
                return {"errors": msg}, self.HASSAD_REQUEST_NOT_ACCEPTED
            else:
                logger.error("Error in hassad redeem point api, {}"
                             "".format(response.text))
                msg = self.MESSAGE.get(self.HASSAD_CONNECTION_ERROR)
                return {"errors": msg}, self.HASSAD_CONNECTION_ERROR

        except Exception as e:
            error = "Exception in hassad redeem point api: {}".format(e)
            logger.error("Exception in hassad redeem point api: "
                         "{}".format(e), exc_info=True)
            return {"errors": error}, self.HASSAD_CONNECTION_ERROR

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

    def handle_hassad_response(self, response_data, payment_data):
        message = "API request completed successfully"

        logger.info(
            "handle_hassad_response data {}".format(response_data))
        is_success, is_redirect, redirect_url = False, False, None
        update_data = {}
        data = {}
        partner_response = response_data.get('partner_response') or {}
        name_on_card = partner_response.get("customer_name", "")
        language = payment_data.language
        is_full_redemption = partner_response.get("is_full_redemption", False)

        if is_full_redemption is False:
            redirect_url = (partner_response.get('url') or
                            partner_response.get('action', {}).get('url'))
            if redirect_url:
                is_success = True
                is_redirect = True
                self.payment_status = PAYMENT_STATUS_PENDING
                self.point_collection_enabled = (
                    auto_enable_or_disable_point_collection(
                        Q(
                            payment_method=PAYMENT_METHOD_HASSAD,
                            active=True,
                            earn_on_partial_redemption=True
                        ))
                )
                self.redeemed_amount = partner_response.get('redeemed_amount')
                self.redeemed_point = partner_response.get(
                    'redeemedTouchPoints')
                self.payable_amount = partner_response.get('checkout_amount')
                self.points_redeemed_mobile_number = partner_response.get(
                    'redeemed_mobile_number')
                self.point_program = PAYMENT_METHOD_HASSAD

                data = {
                    "id": partner_response.get("id"),
                    "status": partner_response.get("status"),
                    "type": partner_response.get("type"),
                    "action": partner_response.get("action")
                }

            else:
                redirect_url = ('{}?transaction_id={}'.format(
                    payment_data.failure_url,
                    payment_data.transaction_id))
                is_success = False
                is_redirect = True
                message = self.hassad_error_response_message(
                    response_data, language)
                if partner_response.get("status") == PAYMENT_DECLINED_STATUS:
                    message = partner_response.get("decline_reason")

                self.payment_status = PAYMENT_STATUS_DECLINED
        else:
            if response_data.get('code') == self.SUCCESS:
                self.payment_status = PAYMENT_STATUS_PAID
                self.approved = True
                paid_amount = partner_response.get('invoice_amount')
                if paid_amount:
                    self.amount = paid_amount
                    update_data['amount'] = self.amount

                self.redeemed_amount = float(
                    partner_response.get('redeemed_amount'))
                self.redeemed_point = partner_response.get(
                    'redeemedTouchPoints')

                self.payable_amount = 0
                self.service_fee = 0
                self.VAT_amount = 0

                self.points_redeemed_mobile_number = partner_response.get(
                    'redeemed_mobile_number')
                self.point_program = PAYMENT_METHOD_HASSAD

                redirect_url = ('{}?transaction_id={}'.format(
                    payment_data.success_url, payment_data.transaction_id))
                is_success, is_redirect = True, True
            else:
                self.payment_status = PAYMENT_STATUS_DECLINED_RETRY
                is_redirect = False
                message = self.hassad_error_response_message(
                    response_data, language)

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
            "hassad_response": response_data,
            "is_success": is_success
        }
        if data and partner_response.get('is_payment_success'):
            return_response["data"] = data
        return return_response

    def hassad_error_response_message(self, response_data, language):
        message = ""
        try:
            code = response_data.get("code")
            partner_response = response_data.get('partner_response')
            if code == self.HASSAD_PAYMENT_FAILED:
                message = partner_response.get("checkout_response_data",
                                               {}).get("response_summary", "")
            elif language == LANGUAGE_CODE_AR:
                message = partner_response.get("response_text_ar")
            elif partner_response.get("response_text"):
                message = partner_response.get("response_text")
            else:
                message = self.MESSAGE.get(code)
        except Exception as e:
            logger.error(
                "{} Exception occurred on {}, err {} ".format(
                    self.class_name, inspect.currentframe().f_code.co_name,
                    e))

        return message

    def prepare_redeem_payload(self, transaction_data):
        """
        prepares payload for Hassad redeem api
        """
        payment_reference = ''
        if transaction_data.get("payment_reference"):
            payment_reference = ("&redemption_reference_id=" +
                                 transaction_data.get("payment_reference"))
        params = ('?id=' + self.request_data.get("encrypted_id") +
                  payment_reference + "&redemption_partner=HASSAD")
        redeem_payload = {
            "response_url": add_payment_gateway_info_in_url(
                transaction_data=transaction_data,
                app_config=get_app_config(),
                params=params,
                code=HASSAD_CLIENT_CODE,
            ),
            "invoice_id": self.transaction_obj.invoice_id,
            "customer_ip_address": self.transaction_obj.ip,
            "channel_code": get_channel_code(self.transaction_obj),
            "client_code": HASSAD_CLIENT_CODE,
            "customer_uid": self.transaction_obj.customer_uid
        }
        return redeem_payload

    @staticmethod
    def handle_hassad_collection(transaction_obj):
        """
        Updating program, mobile number... on Hassad Verification
        """
        if transaction_obj.point_collection_enabled:
            if (transaction_obj.point_program != PAYMENT_METHOD_HASSAD or
                    not transaction_obj.points_collected_mobile_number):
                transaction_obj.points_collected_mobile_number = (
                    transaction_obj.points_redeemed_mobile_number)
                transaction_obj.point_program = PAYMENT_METHOD_HASSAD
                transaction_obj.save()
