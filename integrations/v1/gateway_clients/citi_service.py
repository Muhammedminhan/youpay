import json
import logging
import requests
from decimal import Decimal
from rest_framework import status
from core.constants import REQUEST_METHOD_POST, PAYMENT_GATEWAY_CITIREWARDS
from core.utils import get_payment_gateway_config
from integrations.constants import (
    CITI_REWARDS_CACHE_KEY, CITI_REWARDS_HUB_CODE, CITI_GENERATE_OTP_API,
    PAYMENT_REQUEST_GENERATE_OTP, CITI_REWARDS_CONNECTION_ERROR_MESSAGE,
    CITI_REWARDS_SUCCESS_CODE, CITI_REWARDS_MFA_REQUIRED_CODE,
    CITI_POINT_BALANCE_API, PAYMENT_REQUEST_POINT_BALANCE,
    CITI_REDEMPTION_API, PAYMENT_REQUEST_REDEMPTION
)
from integrations.v1.gateway_clients.utils import (
    get_citi_converted_amount, format_citi_service_error_response)
from integrations.v1.serializers.citi_rewards_request import (
    GenerateOTPRequestSerializer)
from payments.constants import (
    PAYMENT_STATUS_INITIATED, PAYMENT_METHOD_CITI_REWARDS,
    PAYMENT_STATUS_PAID, PAYMENT_STATUS_PENDING)
from services.v1.views.common import is_redirect
from services.v1.views.payment import PaymentRequestView
from services.v1.views.payment_handlers import PaymentHandlers

logger = logging.getLogger(__name__)


class CitiRewardsManager(PaymentHandlers, PaymentRequestView):
    """
    Class to manage citi rewards related operations
    """

    def __init__(self):
        self.payment_reference = None
        self.payment_status = None
        self.transaction_id = None
        self.citi_reward_config = get_payment_gateway_config(
            CITI_REWARDS_CACHE_KEY, CITI_REWARDS_HUB_CODE)

    def get_payment_header(self):
        """
        Returns headers
        """
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.citi_reward_config.api_key,
            'X-API-KEY': self.citi_reward_config.api_key
        }
        return headers

    def get_generate_otp_data(self, data):
        """
        Returns request data for calling citi rewards generate otp api
        """
        if data.get('transaction_data') and data.get('request_data'):
            payment_data = GenerateOTPRequestSerializer(data)
            return payment_data.data
        else:
            logger.error(
                "transaction_data or request_data data is not "
                "available for citi rewards generate otp api")
            return None

    def generate_otp(self, data):
        """
        calls citi rewards point otp generating api and returns the balance
        """
        transaction_data = data.get('transaction_data')
        self.transaction_id = transaction_data.get('transaction_id')
        self.payment_status = transaction_data.get('payment_status')

        verify_response, verify_status = self.verify_transaction(
            transaction_data)
        is_verified = verify_response.get('is_verified', False)

        """if transaction is verified then proceed with payment"""
        try:
            if verify_status == status.HTTP_200_OK and is_verified:
                if self.citi_reward_config:
                    payment_data = self.get_generate_otp_data(data)
                    logger.info(
                        "Youpay sending payment data to citi rewards point"
                        " generate otp api is {}".format(payment_data))
                    payload = json.dumps(payment_data)
                    url = (self.citi_reward_config.domain +
                           CITI_GENERATE_OTP_API)
                    headers = self.get_payment_header()

                    transaction_obj = self.get_youpay_transaction_data(
                        self.transaction_id)
                    response = requests.post(url, data=payload,
                                             headers=headers)
                    logger.info("Response from Citi Rewards generate OTP "
                                "api is {}".format(response))

                    # storing Youpay to payment gateway
                    # request and response data
                    self.create_youpay_to_payment_gateways_data(
                        transaction_obj=transaction_obj,
                        transaction_id=self.transaction_id,
                        request_data=payload,
                        response_data=response.text,
                        request_method=REQUEST_METHOD_POST,
                        request_type=PAYMENT_REQUEST_GENERATE_OTP
                    )

                    if response:
                        response_data = response.json()

                        logger.info("citi rewards generate otp api "
                                    "response: {}".format(response_data))
                        if (response.status_code == 200 and
                                response_data.get('code') in
                                [CITI_REWARDS_SUCCESS_CODE,
                                 CITI_REWARDS_MFA_REQUIRED_CODE]):
                            self.payment_reference = response_data.get(
                                "reference_id")
                            response_data.update({'is_success': True})
                            self.payment_status = PAYMENT_STATUS_INITIATED

                            self.update_youpay_transaction_data(
                                {
                                    "transaction_id": self.transaction_id,
                                    "payment_status": self.payment_status,
                                    "payment_method": (
                                        PAYMENT_METHOD_CITI_REWARDS),
                                    "payment_reference": (
                                        self.payment_reference
                                    ),
                                    "payment_gateway": (
                                        PAYMENT_GATEWAY_CITIREWARDS),
                                    "card_last4": payment_data.get(
                                        "card_last4")
                                }
                            )
                            return response_data, self.SUCCESS
                        code = format_citi_service_error_response(
                            response_data
                        )
                        logger.warning("Error in citi rewards generate "
                                       "otp api, {}".format(response_data))
                        return None, code
                    logger.error("Error in citi rewards generate "
                                 "otp api, {}".format(response.text))
                    return (None,
                            self.CITI_REWARDS_CONNECTION_ERROR)
                else:
                    logger.error(CITI_REWARDS_CONNECTION_ERROR_MESSAGE)
                    return None, self.CITI_REWARDS_CONNECTION_ERROR
            else:
                msg = (
                    "Youpay transaction verification failed for citi rewards"
                    "for transaction id {} response is : "
                    "{} ".format(self.transaction_id, verify_response))
                logger.error(msg)
                return (verify_response,
                        self.CLIENT_TRANSACTION_VERIFICATION_FAILED)
        except Exception as e:
            error = "Error in citi rewards otp generating api: {}".format(e)
            logger.error(error)
            return None, self.CITI_REWARDS_CONNECTION_ERROR

    def get_point_balance(self, data):
        """
        calls citi rewards point balance api and returns the balance
        """
        url = self.citi_reward_config.domain + CITI_POINT_BALANCE_API
        self.transaction_id = data.get('transaction_id')

        payload = {
            'reference_id': data.get('reference_id'),
            'pin_number': data.get('pin_number'),
        }

        transaction_obj = self.get_youpay_transaction_data(
            self.transaction_id)
        if transaction_obj is None:
            return None, self.TRANSACTION_NOT_FOUND
        try:
            point_balance_payload = json.dumps(payload)
            logger.info(
                "Youpay sending request data to citi reward point balance "
                "api is {}".format(payload))
            headers = self.get_payment_header()
            response = requests.post(url, data=point_balance_payload,
                                     headers=headers)
            logger.info("Response from Citi Rewards get point balance api"
                        " is {}".format(response))
            self.create_youpay_to_payment_gateways_data(
                transaction_obj=transaction_obj,
                transaction_id=self.transaction_id,
                request_data=point_balance_payload,
                response_data=response.text,
                request_method=REQUEST_METHOD_POST,
                request_type=PAYMENT_REQUEST_POINT_BALANCE
            )
            if response:
                response_data = response.json()
                logger.info("citi rewards point balance api response is: "
                            "{}".format(response_data))
                if (
                        response.status_code == 200 and
                        response_data.get('code') == CITI_REWARDS_SUCCESS_CODE
                ):
                    self.payment_reference = response_data.get(
                        "reference_id")
                    deducting_points = get_citi_converted_amount(
                        response_data, transaction_obj.amount)
                    response_data.update({
                        'is_success': True,
                        'redeem_points': deducting_points
                    })

                    self.update_youpay_transaction_data(
                        {
                            "transaction_id": self.transaction_id,
                            "available_points": response_data.get(
                                'available_points'),
                            "maximum_redeemable_points": response_data.get(
                                'maximum_redeem_point'),
                            "minimum_redeemable_points": response_data.get(
                                'minimum_redeem_point'),
                            "amount_conversion_rate": Decimal(
                                response_data.get(
                                    'conversion_rate')),
                            "payment_reference": self.payment_reference,
                            'payment_status': PAYMENT_STATUS_PENDING
                        }
                    )
                    return response_data, self.SUCCESS
                code = format_citi_service_error_response(
                    response_data
                )
                logger.warning("Error in citi rewards get points "
                               "api, {}".format(response_data))
                return None, code
            logger.error("Error in citi rewards generate point balance "
                         "api, {}".format(response.text))
            return None, self.CITI_REWARDS_CONNECTION_ERROR
        except Exception as e:
            error = "Error in citi rewards point balance api: {}".format(e)
            logger.error(error)
            return None, self.CITI_REWARDS_CONNECTION_ERROR

    def point_redemption(self, data):
        """
        calls citi rewards point redemption api
        """
        url = self.citi_reward_config.domain + CITI_REDEMPTION_API
        self.transaction_id = data.get('transaction_id')

        payload = {
            'reference_id': data.get('reference_id'),
            'description': data.get('reference_id'),
        }
        transaction_obj = self.get_youpay_transaction_data(
            self.transaction_id)
        point_redemption_payload = json.dumps(payload)
        if transaction_obj is None:
            return None, self.TRANSACTION_NOT_FOUND
        if transaction_obj.payment_status == PAYMENT_STATUS_PAID:
            response_data = {
                "is_redirect": True,
                "is_success": True,
                "redirect_url": (transaction_obj.success_url +
                                 '?transaction_id=' + self.transaction_id),
                "transaction_message": {
                    "status": 200,
                    "is_capture": True,
                    "message": "Transaction already redeemed"
                }
            }
            self.create_youpay_to_payment_gateways_data(
                transaction_obj=transaction_obj,
                transaction_id=self.transaction_id,
                request_data=point_redemption_payload,
                response_data=response_data,
                request_method=REQUEST_METHOD_POST,
                request_type=PAYMENT_REQUEST_REDEMPTION
            )
            return response_data, self.SUCCESS

        try:
            logger.info(
                "Youpay sending request data to citi reward point redemption "
                "api is {}".format(payload))
            headers = self.get_payment_header()
            response = requests.post(url, data=point_redemption_payload,
                                     headers=headers)
            logger.info("Response from Citi Rewards get point redemption api"
                        " is {}".format(response))
            self.create_youpay_to_payment_gateways_data(
                transaction_obj=transaction_obj,
                transaction_id=self.transaction_id,
                request_data=point_redemption_payload,
                response_data=response.text,
                request_method=REQUEST_METHOD_POST,
                request_type=PAYMENT_REQUEST_REDEMPTION
            )
            if response:
                response_data = response.json()
                logger.info("citi rewards point balance redemption api "
                            "response is: {}".format(response_data))
                if (
                        response.status_code == 200 and
                        response_data.get('code') == CITI_REWARDS_SUCCESS_CODE
                ):
                    self.payment_reference = response_data.get(
                        "reference_id")
                    self.update_youpay_transaction_data(
                        {
                            'citi_order_id': response_data.get('order_id'),
                            'available_points': response_data.get(
                                'available_point_balance'),
                            'is_full_redemption': True,
                            "redeemed_points": Decimal(response_data.get(
                                'redeemed_points')),
                            "redeemed_amount": transaction_obj.amount,
                            'payment_status': PAYMENT_STATUS_PAID,
                            "transaction_id": self.transaction_id,
                        })

                    redirect_flag, response_data = is_redirect(
                        self.transaction_id, response_data)
                    return response_data, self.SUCCESS
                code = format_citi_service_error_response(
                    response_data
                )
                logger.warning("Error in citi rewards point redemption "
                               "api, {}".format(response_data))
                return None, code
            logger.error("Error in citi rewards generate point balance "
                         "api, {}".format(response.text))
            return None, self.CITI_REWARDS_CONNECTION_ERROR
        except Exception as e:
            error = "Error in citi rewards point redemption api: {}".format(e)
            logger.error(error)
            return None, self.CITI_REWARDS_CONNECTION_ERROR
