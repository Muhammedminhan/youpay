import inspect
import json
import logging

import requests
from rest_framework import status

from core.constants import (PAYMENT_GATEWAY_B2CPAYBACK, REQUEST_METHOD_POST,
                            REQUEST_METHOD_GET)
from core.messages import IS_REDIRECT, REDIRECT_URL, IS_SUCCESS
from core.utils import (get_app_config,
                        decrypt_string,
                        get_config_from_payment_configurations)
from integrations.constants import (ANB_CLIENT_CODE, B2CP_OTP_GENERATION_API,
                                    PAYMENT_REQUEST_GENERATE_OTP,
                                    CHECKOUTPG_PAYMENT_CONFIGURATIONS,
                                    B2CP_REDEEM_POINTS_API,
                                    PAYMENT_REQUEST_REDEMPTION,
                                    B2CP_VERIFY_API, PAYMENT_REQUEST_VERIFY,
                                    PAYMENT_DECLINED_STATUS)
from integrations.v1.gateway_clients.utils import format_verify_data
from integrations.v1.serializers.anb_serializer import (
    AnbPaymentRequestSerializer)
from payments.constants import (PAYMENT_METHOD_ANB, PAYMENT_STATUS_PENDING,
                                PAYMENT_METHOD_ANB_AND_CARD,
                                PAYMENT_STATUS_DECLINED,
                                PAYMENT_STATUS_PAID,
                                LANGUAGE_CODE_AR)
from payments.serializers.youpay_payments import (
    YouPayTransactionDataSerializer)
from services.v1.views.common import add_payment_gateway_info_in_url
from services.v1.views.payment import PaymentRequestView
from services.v1.views.payment_handlers import PaymentHandlers

logger = logging.getLogger(__name__)


class AnbServiceManager(PaymentHandlers, PaymentRequestView):
    """
    Class to manage AnB related operations
    """

    def __init__(self):
        self.anb_config = None
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
        self.points_redeemed_cif_number = None
        self.point_program = None
        self.brand_calculations = None

    def get_payment_header(self):
        """
        Returns headers
        """
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.anb_config.api_key,
            'X-API-KEY': self.anb_config.api_key
        }
        return headers

    @staticmethod
    def get_anb_payment_data(data):
        """
        returns data to be passed to b2c_payback
        """
        if data.get('transaction_obj'):
            payment_data = AnbPaymentRequestSerializer(data)
            return payment_data.data
        else:
            logger.error("transaction_data or request_data is not available")
            return None

    def generate_otp(self, data):
        """
        calls AnB otp generating api and returns otp
        Args:
            data (dict): Data for generating otp request.
        Returns:
            Tuple containing status code and response data.
        """
        try:
            request_data = data.get('request_data')
            self.transaction_obj = request_data.get('transaction_obj')
            self.anb_config = get_config_from_payment_configurations(
                self.transaction_obj, PAYMENT_METHOD_ANB)
            self.transaction_id = self.transaction_obj.transaction_id
            payload = self.get_anb_payment_data(request_data)
            # Dynamically determine the key and value for 'mobile_number' or
            # 'cif_number'
            mobile_or_cif_key_name, mobile_or_cif_key_value = None, None
            if 'mobile_number' in request_data:
                mobile_or_cif_key_name, mobile_or_cif_key_value = (
                    'anb_phone_number', request_data['mobile_number'])
            elif 'cif_number' in request_data:
                mobile_or_cif_key_name, mobile_or_cif_key_value = (
                    'anb_cif_number', request_data['cif_number'])
            else:
                raise ValueError(
                    "Neither 'mobile_number' nor 'cif_number' is present in "
                    "the request data.")

            data = {
                'transaction_id': str(self.transaction_id),
                mobile_or_cif_key_name: mobile_or_cif_key_value,
                'source_payment_method': PAYMENT_METHOD_ANB
            }
            payload.update(data)
            self.request_data = payload
            payload['apiclient'] = self.transaction_obj.api_client.name
            payload['client_code'] = ANB_CLIENT_CODE
            
            logger.info("anb config is {}".format(self.anb_config))

            url = self.anb_config.domain + B2CP_OTP_GENERATION_API
            headers = self.get_payment_header()
            logger.info(
                "Youpay sending request data to AnB generate otp api {}"
                "is {} for transaction id {} with header {}".format(
                    url, payload, self.transaction_id, headers))
            response = requests.post(url, data=json.dumps(payload),
                                     headers=headers)

            if response.status_code == status.HTTP_200_OK:
                response_data = response.json()
                logger.info("AnB payment response: {} for transaction "
                            "id {}".format(response_data,
                                           self.transaction_id))
                self.response_data = response_data.get('partner_response')
                self.update_youpay_transaction_data({
                    'transaction_id': self.transaction_obj.transaction_id,
                    'payment_reference': self.response_data.get(
                        'payment_reference'),
                    'points_redeemed_mobile_number': mobile_or_cif_key_value,
                })
                return response_data, self.SUCCESS

            logger.error("Error in AnB otp, {} for transaction id {}".format(
                response.json(), self.transaction_id))
            self.response_data = response.json()
            error_code = self.response_data.get('code')
            return ({"error": response.json()},
                    error_code)
        except Exception as e:
            error = ("Exception in AnB generate otp api: {} for "
                     "transaction id {}").format(e, self.transaction_id)
            logger.error(error, exc_info=True)
            self.response_data = {}
            return {"error": error}, self.ANB_CONNECTION_ERROR
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
        calls AnB points redeem api

        Args:
            data (dict): The transaction and payment details for the
            redemption request.
        Returns:
            tuple: A response dictionary containing the API response data and
            a status code.
        """
        try:
            self.request_data = data
            self.transaction_obj = self.request_data.get('transaction_obj')
            self.anb_config = get_config_from_payment_configurations(
                self.transaction_obj, PAYMENT_METHOD_ANB)
            self.transaction_id = self.transaction_obj.transaction_id
            payload = self.request_data
            serializer = YouPayTransactionDataSerializer(self.transaction_obj)
            transaction_data = serializer.data
            payload.update(self.prepare_redeem_payload(transaction_data))
            payload.pop('transaction_obj')
            self.payment_method = (PAYMENT_METHOD_ANB_AND_CARD
                                   if float(self.request_data.get(
                                        'checkout_amount')) > 0 else
                                   PAYMENT_METHOD_ANB)
            payload.update({"source_payment_method": self.payment_method})
            verify_response, verify_status = self.verify_transaction(
                transaction_data, payment_method=PAYMENT_METHOD_ANB)
            if not verify_response:
                msg = (
                    "Youpay AnB transaction verification failed for"
                    " transaction id {} response is : {} ".format(
                        self.transaction_id, verify_response))
                logger.error(msg)
                return (verify_response,
                        self.CLIENT_TRANSACTION_VERIFICATION_FAILED)
            is_verified = verify_response.get('is_verified', False)
            if not is_verified and verify_response:
                msg = (
                    "Youpay AnB transaction verification failed for"
                    " transaction id {} response is : {} ".format(
                        self.transaction_id, verify_response))
                logger.error(msg)
                self.response_data = verify_response
                return (verify_response,
                        self.CLIENT_TRANSACTION_VERIFICATION_FAILED)
            url = self.anb_config.domain + B2CP_REDEEM_POINTS_API
            headers = self.get_payment_header()
            logger.info(
                "Youpay sending request data to anb redeem point api for "
                "transaction id {} is {} headers {} ".format(
                    payload, self.transaction_id, headers))
            response = requests.post(url, data=json.dumps(payload),
                                     headers=headers)
            if response.status_code == status.HTTP_200_OK:
                response_data = response.json()
                self.response_data = response_data
                logger.info("anb redeem point api response: {}".format(
                    response_data))
                response_data = self.handle_anb_response(
                    response_data, self.transaction_obj)
                return response_data, self.SUCCESS
            elif response.status_code == 400:
                response_data = response.json()
                self.response_data = response_data
                response_data = self.handle_anb_response(
                    response_data, self.transaction_obj)
                response_code = response_data.get("anb_response", {}).get(
                    "code")
                logger.info("anb redeem point api response: {} for {}".format(
                                response_data, self.transaction_id))
                return response_data, response_code
            else:
                logger.error("Error in anb redeem point api, {}"
                             "".format(response.text))
                msg = self.MESSAGE.get(self.ANB_CONNECTION_ERROR)
                return {"errors": msg}, self.ANB_CONNECTION_ERROR
        except Exception as e:
            error = "Exception in anb redeem point api: {}".format(e)
            logger.error("Exception in anb redeem point api: "
                         "{}".format(e), exc_info=True)
            return {"errors": error}, self.ANB_CONNECTION_ERROR
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

    def prepare_redeem_payload(self, transaction_data):
        """
        prepares payload for AnB redeem api

        Args:
            'transaction_data' containing transaction details
        Returns:
            'payload' for the AnB redeem API
        """
        payment_reference = ''
        if transaction_data.get("payment_reference"):
            payment_reference = ("&redemption_reference_id=" +
                                 transaction_data.get("payment_reference"))
        params = ('?id=' + self.request_data.get("encrypted_id") +
                  payment_reference + "&redemption_partner=ANB")
        redeem_payload = {
            "response_url": add_payment_gateway_info_in_url(
                transaction_data=transaction_data,
                app_config=get_app_config(),
                params=params,
                code=ANB_CLIENT_CODE,
            ),
            "invoice_id": self.transaction_obj.invoice_id,
            "customer_ip_address": self.transaction_obj.ip,
            "channel_code": CHECKOUTPG_PAYMENT_CONFIGURATIONS.get(
                transaction_data.get("currency").upper()),
            "client_code": ANB_CLIENT_CODE,
            "customer_uid": self.transaction_obj.customer_uid
        }
        return redeem_payload

    def anb_error_response_message(self, response_data, language):
        """
        Retrieves the appropriate error message from the AnB API response.

        Args:
            response_data (dict): The response data from the AnB API.
            language (str): The language code to determine the error message
            format.
        Returns:
            message (str): The extracted error message based on the response
            data.
        """
        message = ""
        try:
            code = response_data.get("code")
            partner_response = response_data.get('partner_response')
            if code == self.ANB_PAYMENT_FAILED:
                message = partner_response.get("checkout_response_data",
                                               {}).get("response_summary",
                                                       "")
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

    def handle_anb_response(self, response_data, payment_data):
        """
        Processes the response from the AnB API and updates youpay transaction
        data accordingly.

        Args:
            response_data: The response data from the AnB API.
            payment_data: Payment transaction object
        Returns:
            Dictionary containing redirection url, AnB response, success
            status etc.
        """
        message = "API request completed successfully"
        youpay_update_data = {}
        logger.info(
            "handle_anb_response data {}".format(response_data))
        is_success, is_redirect, redirect_url = False, False, None
        update_data = {}
        data = {}
        partner_response = response_data.get('partner_response')
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
                self.redeemed_amount = partner_response.get('redeemed_amount')
                self.redeemed_point = partner_response.get(
                    'redeemedTouchPoints')
                self.payable_amount = partner_response.get('checkout_amount')
                self.points_redeemed_mobile_number = partner_response.get(
                    'redeemed_mobile_number')
                self.point_program = PAYMENT_METHOD_ANB
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
                message = self.anb_error_response_message(response_data,
                                                              language)
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
                self.point_program = PAYMENT_METHOD_ANB
                redirect_url = ('{}?transaction_id={}'.format(
                    payment_data.success_url, payment_data.transaction_id))
                is_success, is_redirect = True, True
            else:
                self.payment_status = PAYMENT_STATUS_DECLINED
                is_redirect = True
                redirect_url = ('{}?transaction_id={}'.format(
                    payment_data.failure_url,
                    payment_data.transaction_id))
                message = self.anb_error_response_message(response_data,
                                                              language)
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
            "anb_response": response_data,
            "is_success": is_success
        }
        if data and partner_response.get("is_payment_success"):
            return_response["data"] = data
        return return_response

    def verification(self, request_data):
        """
        AnB Verification with b2c

        Args:
            request_data (dict):  Contains transaction details.
        Returns:
            return_response_data: Processed response.
            transaction_obj (obj): Payment transaction object.
        """
        payment_scheme = None
        request_transaction_id = request_data.get('transaction_id')
        logger.info(
            "Anb Verification with b2c started for transaction {}, data --> "
            "{}".format(request_transaction_id, request_data))
        if request_transaction_id:
            try:
                transaction_id = decrypt_string(request_transaction_id)
                transaction_obj = self.get_youpay_transaction_data(
                    transaction_id)
                formatted_data = format_verify_data(request_data,
                                                    transaction_obj)
                gateway_obj = get_config_from_payment_configurations(
                    transaction_obj, PAYMENT_METHOD_ANB)
                anb_domain = gateway_obj.domain
                url = (anb_domain + B2CP_VERIFY_API +
                       "?&redemption_partner=ANB")
                headers = {'Content-Type': 'application/json'}
                formatted_data.pop("transaction_id")
                response = requests.get(url, params=formatted_data,
                                        headers=headers)
                return_response_data = {}
                if response.status_code == status.HTTP_200_OK and (
                        response.json().get(
                            "status").lower() == PAYMENT_STATUS_PAID):
                    """Redemption verified successfully"""
                    logger.info(
                        "Anb Verification with b2c completed for transaction "
                        "{}".format(transaction_id))

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
                from services.v1.api_clients.anb_service import (
                 get_calculated_youpay_transaction_data_with_anb_balance)

                """update youpay transaction data with anb balance 
                calculation on successful payment"""
                calculated_youpay_transaction_data = (
                 get_calculated_youpay_transaction_data_with_anb_balance(
                        transaction_obj))
                update_data = {
                    'transaction_id': str(transaction_obj.transaction_id),
                    'payment_status': payment_status,
                    'is_flagged': is_flagged,
                    'approved': approved,
                    'is_gcc_card': is_gcc_card,
                    'card_last4': card_last4,
                    'card_bin': card_bin,
                    'card_issuer_country': card_issuer_country,
                    'payment_scheme': payment_scheme
                }
                update_data.update(calculated_youpay_transaction_data)
                logger.info("Anb Verification with b2c completed for "
                            "transaction {}, data to be updating {}".format(
                                transaction_id, update_data))
                self.update_youpay_transaction_data(update_data)
                return return_response_data, transaction_obj
            except Exception as e:
                logger.error(
                    "Verify api call to Anb failed for transaction {}"
                    .format(request_transaction_id), exc_info=e)
                return None, None
        else:
            logger.error("Invalid transaction id ({}) received for Anb "
                         "verify api".format(request_transaction_id))
            return None, None
