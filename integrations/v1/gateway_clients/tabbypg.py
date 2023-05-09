import json
import logging

import requests
from django.shortcuts import redirect
from rest_framework import status
from rest_framework.views import APIView

from core.constants import (
    REQUEST_METHOD_POST, PAYMENT_GATEWAY_TABBYPG, REQUEST_METHOD_GET)
from core.messages import IS_REDIRECT, IS_SUCCESS, REDIRECT_URL
from core.utils import (get_payment_gateway_config, get_redirect_url,
                        tabby_reject_check)
from integrations.constants import (
    TABBYPG_CREATE_PAYMENT_ENDPOINT,
    PAYMENT_REQUEST_TYPE_PAYMENT, TABBYPG_CACHE_KEY, TABBYPG_HUB_CODE,
    TABBYPG_VERIFY_PAYMENT_ENDPOINT, PAYMENT_REQUEST_VERIFY
)
from integrations.messages import TABBYPG_CONNECTION_ERROR_MESSAGE
from integrations.v1.serializers.tabbypg_payment_request import (
    TabbyPGPaymentRequestSerializer
)
from payments.constants import (
    PAYMENT_STATUS_CANCELLED, PAYMENT_STATUS_PENDING, PAYMENT_STATUS_PAID,
    PAYMENT_METHOD_TABBY_UAE, PAYMENT_METHOD_TABBY_KSA,
    PAYMENT_STATUS_FAILED, PAYMENT_STATUS_REJECTED,
    PAYMENT_STATUS_REJECTED_RETRY)
from services.constants import CURRENCY_UAE
from services.v1.views.common import YouPayTransactionCRUD, is_redirect
from services.v1.views.payment import PaymentRequestView
from services.v1.views.payment_handlers import PaymentHandlers

logger = logging.getLogger(__name__)


class TabbyPGManager(PaymentRequestView, PaymentHandlers):
    def __init__(self):

        self.tabbypg_config = get_payment_gateway_config(TABBYPG_CACHE_KEY,
                                                         TABBYPG_HUB_CODE)
        self.transaction_id = None
        self.payment_method = None
        self.payment_gateway = PAYMENT_GATEWAY_TABBYPG
        self.payment_status = None
        self.payment_reference = None
        self.channel_code = None
        self.request_data = None
        self.response_data = None
        self.request_type = None
        self.request_method = None
        self.transaction_obj = None
        self.currency = None

    def prepare_data_to_update(self):

        data_to_update = {
            'transaction_id': self.transaction_id,
            "payment_status": self.payment_status,
            "payment_reference": self.payment_reference,
            "payment_gateway": self.payment_gateway,
            "channel_code": self.channel_code,
            "payment_method": self.payment_method,
        }

        return data_to_update

    def get_tabbypg_payment_data(self, data):

        if data.get('transaction_data') and data.get('request_data'):
            payment_data = TabbyPGPaymentRequestSerializer(data)
            return payment_data.data
        else:
            logger.error(
                "transaction_data or request_data data is not available")
            return None

    def get_payment_header(self):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.tabbypg_config.api_key,
            'Api-key': self.tabbypg_config.api_key
        }
        return headers

    def set_payment_method(self, transaction_obj):
        """
        returns: payment methos based on currency
        """
        if transaction_obj:
            if transaction_obj.currency == CURRENCY_UAE:
                self.payment_method = PAYMENT_METHOD_TABBY_UAE
            else:
                self.payment_method = PAYMENT_METHOD_TABBY_KSA

    def create_session(self, data):
        """
        Method for creating session with Tabbypg
        Step 1 : get transaction id
        Step 2 : get youpaytransaction data corresponding to transaction id
        Step 3 : communicate with tabbypg gateway to create session
        Step 4 : update youpaytransaction
        """

        transaction_data = data.get('transaction_data')

        self.transaction_id = transaction_data.get('transaction_id')
        self.payment_status = transaction_data.get('payment_status')
        self.payment_reference = transaction_data.get('payment_reference')
        transaction_obj = self.get_youpay_transaction_data(
            self.transaction_id)
        self.set_payment_method(transaction_obj)
        self.currency = transaction_data.get('currency')
        verify_response, verify_status = self.verify_transaction(
            transaction_data)
        logger.info(
            "Verify response: {} - {}".format(verify_status, verify_response))

        is_verified = verify_response.get('is_verified', False)

        """if transaction is verified then proceed with payment"""
        try:
            if verify_status == status.HTTP_200_OK and is_verified:
                tabbypg_conf = self.tabbypg_config
                if tabbypg_conf:
                    payment_data = self.get_tabbypg_payment_data(data)
                    logger.info(
                        "Youpay sending payment data is {}".format(
                            payment_data))
                    payment_data_to_send = json.dumps(payment_data)
                    url = (self.tabbypg_config.domain +
                           TABBYPG_CREATE_PAYMENT_ENDPOINT)
                    headers = self.get_payment_header()

                    response = requests.post(url, data=payment_data_to_send,
                                             headers=headers)
                    logger.info("TabbyPG response is {}".format(response))
                    response_data = response.json()
                    logger.info("tabbypg payment response: {}"
                                .format(response_data))

                    # storing Youpay to payment gateway request and response data
                    self.create_youpay_to_payment_gateways_data(
                        transaction_obj=transaction_obj,
                        transaction_id=self.transaction_id,
                        request_data=payment_data_to_send,
                        response_data=response.text,
                        request_method=REQUEST_METHOD_POST,
                        request_type=PAYMENT_REQUEST_TYPE_PAYMENT,
                    )

                    if response:
                        response_data = response.json()
                        logger.info("tabbypg payment response: {}"
                                    .format(response_data))
                        if (response_data.get('status') == 200 and
                                response_data.get(IS_REDIRECT) is True):
                            self.payment_reference = response_data.get(
                                "payment_ref_no")

                            self.payment_status = PAYMENT_STATUS_PENDING

                            self.update_youpay_transaction_data(
                                self.prepare_data_to_update())
                            response_data[IS_SUCCESS] = True
                            return response_data, self.SUCCESS

                        logger.error("Error in tabbypg payment, {}".format(
                            response.text))

                        self.payment_reference = response_data.get(
                            "payment_ref_no")
                        self.payment_status = tabby_reject_check(
                            response_data)

                        self.update_youpay_transaction_data(
                            self.prepare_data_to_update())

                        response, code = self.process_tabby_failure_response()

                        return response, code

                    return ({"error": response_data},
                            self.TABBYPG_CONNECTION_ERROR)
                else:
                    logger.error(TABBYPG_CONNECTION_ERROR_MESSAGE)
                    return {None}, self.TABBYPG_CONNECTION_ERROR
            else:
                msg = (
                    "Youpay tabby transaction verification failed, "
                    "transaction id {} response is : {} ".format(
                        self.transaction_id, verify_response))
                logger.error(msg)
                return verify_response, self.CLIENT_TRANSACTION_VERIFICATION_FAILED
        except Exception as e:
            error = "Error in creating session with Tabbypg: {}".format(e)
            logger.error("Exception in tabbypg payment: {}".format(e))
            return {"error": error}, self.TABBYPG_CONNECTION_ERROR

    def verify_session(self, data):
        """
        Method for verifying session with Tabbypg
        """
        url = self.tabbypg_config.domain + TABBYPG_VERIFY_PAYMENT_ENDPOINT
        transaction_id = data.get('transaction_id')

        params = {
            'payment_id': data.get('payment_id'),
        }

        self.transaction_obj = self.get_youpay_transaction_data(
            transaction_id)

        self.transaction_id = transaction_id
        self.request_data = json.dumps(params)
        self.request_type = PAYMENT_REQUEST_VERIFY
        self.request_method = REQUEST_METHOD_GET

        if self.transaction_obj is None:
            return None, self.TRANSACTION_NOT_FOUND

        try:
            # if transaction is already verified then redirect to
            # corresponding client url
            if self.transaction_obj.payment_status == PAYMENT_STATUS_PAID:
                response_data = {
                    "is_redirect": True,
                    "redirect_url": (self.transaction_obj.success_url +
                                     '?transaction_id=' + transaction_id),
                    "transaction_message": {
                        "status": 200,
                        "is_capture": True,
                        "message": "Duplicate verification"
                    }
                }
                self.response_data = json.dumps(response_data)

                return response_data, self.SUCCESS

            response = requests.get(url, params=params)

            if response:
                response_data = response.json()
                logger.info(
                    "Verify payment response data {}".format(response_data))

                if response_data.get('is_capture'):
                    payment_status = PAYMENT_STATUS_PAID
                    approved = True
                    response_summary = "Payment successful"
                else:
                    payment_status = PAYMENT_STATUS_FAILED
                    approved = False
                    response_summary = "Payment failed"

                self.update_youpay_transaction_data(
                    {
                        'transaction_id': transaction_id,
                        "payment_status": payment_status,
                        "approved": approved,
                        "response_summary": response_summary,
                    }
                )
                redirect_flag, response_data = is_redirect(transaction_id,
                                                           response_data)
                if redirect_flag:
                    self.response_data = json.dumps(response_data)
                    return response_data, self.SUCCESS
                else:
                    self.response_data = json.dumps(response_data)
                    return response_data, self.PAYMENT_FAILED
            else:
                logger.error(
                    "Error while verifying_payment status: {}, reason {} "
                    .format(response.status_code, response.reason))
                return None, self.TABBYPG_CONNECTION_ERROR
        except Exception as e:
            logger.error("Exception in tabbypg verify session: {}".format(e))
            return {"error": e}, self.TABBYPG_CONNECTION_ERROR
        finally:
            self.create_youpay_to_payment_gateways_data(
                transaction_obj=self.transaction_obj,
                transaction_id=self.transaction_id,
                request_data=self.request_data,
                response_data=self.response_data,
                request_type=self.request_type,
                request_method=self.request_method,
            )

    def process_tabby_failure_response(self):
        if self.payment_status in [PAYMENT_STATUS_REJECTED,
                                   PAYMENT_STATUS_REJECTED_RETRY]:
            code = self.TABBYPG_PAYMENT_REJECTED
            response = {
                IS_REDIRECT: False,
                IS_SUCCESS: False,
                REDIRECT_URL: None,
                "message": self.MESSAGE.get(code)
            }
            return response, self.TABBYPG_PAYMENT_REJECTED
        else:
            return None, self.TABBYPG_CONNECTION_ERROR


class TabbyPaymentCancel(YouPayTransactionCRUD, APIView):
    """
    This class is used for cancelling payment and redirecting to the
    cancel url in the transaction data
    """

    def get(self, request):
        transaction_id = request.GET.get('transaction_id')

        transaction_object = self.get_youpay_transaction_data(
            transaction_id)

        # update transaction data with cancelled status
        self.update_youpay_transaction_data({
            'transaction_id': transaction_id,
            'payment_status': PAYMENT_STATUS_CANCELLED
        })

        redirect_url = get_redirect_url(transaction_object.cancel_url,
                                        transaction_id)
        logger.info(
            "Youpay Tabby Payment cancelled for transaction_id : {}, "
            "order reference :"
            "{}".format(transaction_id,
                        transaction_object.order_reference))

        return redirect(redirect_url)
