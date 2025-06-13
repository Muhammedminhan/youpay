import json
import logging

import requests
from rest_framework import status

from core.constants import REQUEST_METHOD_POST, PAYMENT_GATEWAY_PAYPAL
from core.utils import get_payment_gateway_config, get_app_config, \
    encrypt_string
from gateways.common import _get_payment_reference_number
from gateways.paypal.constants import (PAYPAL_ORDER_STATUS_CREATED,
                                       PAYPAL_ORDER_ENDPOINT,
                                       PAYPAL_ORDER_STATUS_APPROVED,
                                       PAYPAL_CAPTURE_STATUS_COMPLETED)
from gateways.paypal.models import PaymentAccessToken, PaypalTransaction
from integrations.constants import (PAYMENT_REQUEST_TYPE_CREATE_ORDER,
                                    PAYMENT_REQUEST_TYPE_CAPTURE_ORDER,
                                    PAYPAL_HUB_CODE, PAYPAL_CACHE_KEY)
from payments.constants import (PAYMENT_METHOD_PAYPAL, PAYMENT_STATUS_PENDING,
                                PAYMENT_STATUS_PAID)
from services.utils import get_payment_redirect_url
from services.v1.views.common import (get_saved_fields,
                                      add_payment_gateway_info_in_url)
from services.v1.views.payment import PaymentRequestView
from services.v1.views.payment_handlers import PaymentHandlers

logger = logging.getLogger(__name__)


class PaypalManager(PaymentRequestView, PaymentHandlers):

    def __init__(self):
        self.paypal_config = get_payment_gateway_config(PAYPAL_CACHE_KEY,
                                                        PAYPAL_HUB_CODE)
        self.transaction_id = None
        self.request_data = None
        self.transaction_obj = None
        self.order_reference = None
        self.reference_id = None
        self.payment_status = None
        self.payment_method = None
        self.payment_gateway = PAYMENT_GATEWAY_PAYPAL
        self.paypal_transaction = None
        self.order_id = None

    def create_order(self, request_data):
        try:
            self.payment_method = PAYMENT_METHOD_PAYPAL
            self.payment_status = PAYMENT_STATUS_PENDING
            self.transaction_id = request_data.get('transaction_id')
            self.request_data = request_data
            self.transaction_obj = request_data.get('transaction_obj')
            self.order_reference = request_data.get('order_reference')

            verify_response, verify_status = self.verify_transaction(
                request_data)
            is_verified = verify_response.get('is_verified', False)
            logger.info(
                "Verify response: {} - {}".format(verify_status,
                                                  verify_response))
            if verify_status == status.HTTP_200_OK and is_verified:

                payload = self.create_paypal_order_payload()
                headers = self.get_headers()
                url = self.paypal_config.domain + PAYPAL_ORDER_ENDPOINT

                response = requests.post(
                    url,
                    headers=headers,
                    data=json.dumps(payload)
                )
                logger.info("Paypal create order response for {}: {}".format(
                    self.transaction_id, response.text))

                self.create_youpay_to_payment_gateways_data(
                    transaction_obj=self.transaction_obj,
                    transaction_id=self.transaction_id,
                    request_data=json.dumps(payload),
                    response_data=response.text,
                    request_method=REQUEST_METHOD_POST,
                    request_type=PAYMENT_REQUEST_TYPE_CREATE_ORDER,
                )
                if response:
                    response_data_json = response.json()
                    response_data, response_code = self.handle_paypal_order_response(
                        response_data_json, payload)
                    return response_data, response_code
                logger.error(
                    "Error occurred on paypal create order for "
                    "transaction id {}, {}".format(self.transaction_id,
                                                   response.text))
                return None, self.PAYPAL_CONNECTION_ERROR
            else:
                msg = (
                    "Paypal transaction verification failed, transaction"
                    " id {} response is : {} ".format(self.transaction_id,
                                                      verify_response))
                logger.error(msg)
                return verify_response, self.CLIENT_TRANSACTION_VERIFICATION_FAILED

        except requests.ConnectTimeout as timeout_err:
            error_msg = (
                "Paypal create order request timeout for transaction "
                "{} with error {}".format(
                    self.transaction_id, timeout_err))
            logger.error(error_msg)
            return None, timeout_err
        except requests.ConnectionError as connection_err:
            error_msg = ("Paypal create order connection error for "
                         "transaction id {} with error {}").format(
                self.transaction_id, connection_err)
            logger.error(error_msg)
            return None, self.PAYPAL_CONNECTION_ERROR
        except Exception as e:
            error = (
                "Exception while creating order for transaction {} with error: {}".format(
                    self.transaction_id, e))
            logger.error(error)
            return None, self.PAYPAL_CONNECTION_ERROR

    def create_paypal_order_payload(self):
        customer_name = self.request_data.get('customer_name', '')
        name_parts = customer_name.strip().split()
        payer = {
            'name': {
                'given_name': name_parts[0] if len(name_parts) > 0 else '',
                'surname': name_parts[1] if len(name_parts) > 1 else '',
            },
            'email_address': self.request_data.get('customer_email'),
        }
        self.reference_id = _get_payment_reference_number(
            self.order_reference)

        purchase_units = [{
            "invoice_id": self.reference_id,
            "amount": {
                "currency_code": 'USD',
                "value": float(self.request_data.get('amount')),
            }
        }]

        app_config = get_app_config()
        params = '?id=' + encrypt_string(
            self.request_data.get('encrypted_transaction_id'))

        return_url = add_payment_gateway_info_in_url(
            transaction_data=self.request_data,
            app_config=app_config, params=params,
            code=PAYPAL_HUB_CODE)

        redirect_url = get_payment_redirect_url()
        cancel_url = redirect_url + "{}/{}".format(
            self.transaction_obj.language,
            self.request_data.get('encrypted_transaction_id'))

        application_context = {
            "return_url": return_url,
            "cancel_url": cancel_url
        }

        request_data = {
            'intent': 'CAPTURE',
            'payer': payer,
            'purchase_units': purchase_units,
            'application_context': application_context,
        }

        return request_data

    def handle_paypal_order_response(self, response_data, payment_data):
        status = response_data.get("status")
        order_id = response_data.get("id")
        links = response_data.get("links", [])
        redirect_url = None

        for link in links:
            if link.get("rel") == "approve":
                redirect_url = link.get("href")
                break

        if status == "CREATED" and redirect_url:
            self.update_youpay_transaction_data(
                self.prepare_data_to_update(response_data))
            return_data = {
                "status": 200,
                "is_redirect": True,
                "redirect_url": redirect_url,
                "is_success": True
            }
            self.create_paypal_transaction(response_data)
            return return_data, self.SUCCESS

        logger.error("Unexpected status from PayPal: %s", response_data)
        return None, self.UNKNOWN_ERR

    def get_headers(self):
        gateway_obj = self.paypal_config
        access_token = PaymentAccessToken.get_paypal_access_token(gateway_obj)
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}',
        }
        return headers

    def prepare_data_to_update(self, response_data):
        data_to_update = {
            'transaction_id': self.transaction_id,
            "payment_status": self.payment_status,
            "payment_reference": self.reference_id,
            "payment_method": self.payment_method,
            "payment_gateway": self.payment_gateway,
        }

        return data_to_update

    def create_paypal_transaction(self, response_data):
        try:
            data = {
                "order_id": response_data.get('id'),
                "payment_reference": self.reference_id,
                "status": PAYPAL_ORDER_STATUS_CREATED,
                "amount": self.request_data.get('amount'),
                "currency": self.request_data.get('currency'),
                "customer_name": self.request_data.get('customer_name'),
                "customer_email": self.request_data.get('customer_email'),
                "customer_phone": self.request_data.get('customer_phone'),
            }
            PaypalTransaction.objects.create(**data)

        except Exception as e:
            logger.error(
                "Exception while creating paypal transaction for {}: {}".format(
                    e, self.transaction_id))

    def capture_paypal_order(self, request_data):
        try:
            self.transaction_id = request_data.get('transaction_id')
            self.transaction_obj = request_data.get('transaction_obj')
            self.reference_id = self.transaction_obj.payment_reference
            order_id = request_data.get('order_id')
            self.order_id = order_id
            headers = self.get_headers()
            paypal_transaction = self.get_paypal_transaction()
            order_status = self.check_order_approval(order_id,
                                                     paypal_transaction)

            if order_status["status"] == PAYPAL_ORDER_STATUS_APPROVED:
                url = self.paypal_config.domain + PAYPAL_ORDER_ENDPOINT + '/' + order_id + '/capture'

                response = requests.post(
                    url,
                    headers=headers,
                    data=json.dumps({})
                )
                logger.info("Paypal capture order response for {}: {}".format(
                    self.transaction_id, response.text))

                self.create_youpay_to_payment_gateways_data(
                    transaction_obj=self.transaction_obj,
                    transaction_id=self.transaction_id,
                    request_data=json.dumps({}),
                    response_data=response.text,
                    request_method=REQUEST_METHOD_POST,
                    request_type=PAYMENT_REQUEST_TYPE_CAPTURE_ORDER,
                )

                if response:
                    response_data_json = response.json()
                    response_data, response_code = self.handle_paypal_capture_response(
                        response_data_json, paypal_transaction)
                    return response_data, response_code
                logger.error(
                    "Error occurred on paypal capture order for "
                    "transaction id {}, {}".format(self.transaction_id,
                                                   response.text))
                return None, self.PAYPAL_CONNECTION_ERROR
            elif order_status["status"] == PAYPAL_ORDER_STATUS_CREATED:

                return_data = {
                    "status": 200,
                    "is_redirect": True,
                    "redirect_url": order_status["redirect_url"],
                    "is_success": False,
                    "message": "Paypal Payment Not Complete",
                }
                return return_data, self.PAYAPL_PAYMENT_INCOMPLETE
            else:
                return None, self.PAYPAL_CONNECTION_ERROR

        except requests.ConnectTimeout as timeout_err:
            logger.error(
                "Paypal capture order request timeout for transaction "
                "{} with error {}".format(
                    self.transaction_id, timeout_err))
            return None, self.PAYPAL_CONNECTION_ERROR
        except requests.ConnectionError as connection_err:
            logger.error(
                "Paypal capturing order connection error for transaction id {} with error {}".format(
                    self.transaction_id, connection_err))
            return None, self.PAYPAL_CONNECTION_ERROR
        except Exception as e:
            logger.error(
                "Exception while capturing order for {} with error: {}".format(
                    self.transaction_id, e))
            return None, self.PAYPAL_CONNECTION_ERROR

    def get_paypal_transaction(self):
        try:
            return PaypalTransaction.objects.get(
                payment_reference=self.reference_id, order_id=self.order_id)
        except PaypalTransaction.DoesNotExist:
            logger.error(
                "Paypal transaction not found for order {}".format(
                    self.transaction_id))
            return None

    def handle_paypal_capture_response(self, response_data_json,
                                       paypal_transaction):
        try:
            status = paypal_transaction.status
            purchase_unit = response_data_json.get("purchase_units")
            payments = purchase_unit.get("payments", {})
            capture = payments.get("captures")
            capture_status = capture.get("status", "").upper()
            if capture_status == "COMPLETED":
                return_data = {
                    "status": 200,
                    "is_redirect": True,
                    "redirect_url": self.transaction_obj.success_url,
                    "is_success": True,
                }
                code = self.SUCCESS
                status = PAYPAL_CAPTURE_STATUS_COMPLETED
                response_data_json[
                    'success'] = PAYPAL_CAPTURE_STATUS_COMPLETED
                self.update_youpay_transaction_data({
                    "transaction_id": self.transaction_id,
                    "status": PAYMENT_STATUS_PAID
                })

            else:
                return_data = None
                code = self.PAYPAL_CONNECTION_ERROR

            response_data_json['status'] = status
            self.update_paypal_transaction_data(
                paypal_transaction,
                response_data_json)
            return return_data, code

        except Exception as e:
            logger.error(
                f"Error in handle_paypal_capture_response for "
                f"transaction {self.transaction_id}: {e}")
            return None, self.PAYPAL_CONNECTION_ERROR

    def update_paypal_transaction_data(self, paypal_transaction,
                                                    response_data):
        """Method to update paypal transaction data"""

        data_dict = {}
        try:
            purchase_unit = response_data.get("purchase_units", [{}])[0]
            capture_info = (
                purchase_unit.get("payments", {}).get("captures", [{}])[0])
            payer = response_data.get("payer", {})
            name_data = payer.get("name", {})

            data_dict["capture_id"] = capture_info.get("id")
            data_dict["order_id"] = capture_info.get("id")
            data_dict["status"] = response_data.get("status")
            data_dict["customer_email"] = payer.get("email_address")
            data_dict["payer_id"] = payer.get("payer_id")
            data_dict[
                "customer_name"] = f"{name_data.get('given_name', '')} {name_data.get('surname', '')}".strip()
            data_dict["raw_response"] = response_data

            self.saved_fields = ["updated_at"]
            self.saved_fields = get_saved_fields(self.saved_fields, data_dict,
                                                 paypal_transaction)

            paypal_transaction.save(update_fields=self.saved_fields)

            logger.info(
                "PaypalTransaction updated for order_id {}, status: {}, fields updated: {}".format(
                    paypal_transaction.order_id, paypal_transaction.status,
                    self.saved_fields
                )
            )
            return True
        except Exception as e:
            logger.error(
                "Failed to update PaypalTransaction for order_id {}: {}".format(
                    paypal_transaction.order_id, e))
            return False

    def get_order_details(self, order_id):
        """Call PayPal Show Order Details API"""
        try:
            url = self.paypal_config.domain + PAYPAL_ORDER_ENDPOINT + '/' + order_id
            headers = self.get_headers()
            response = requests.get(url, headers=headers)
            logger.info("Show order details for transaction {}, {}"
                        "".format(response.text, self.transaction_id))
            if response:
                return response.json()
            else:
                logger.error(
                    "Unable to retrieve order details for transaction "
                    "{}, response: {}".format(
                        self.transaction_id, response.text))
                return None
        except Exception as e:
            logger.error("Exception while retrieving order details for "
                         "transaction {}".format(self.transaction_id))
            return None

    def check_order_approval(self, order_id, paypal_transaction):
        """
        Check if PayPal order is APPROVED.
        If CREATED, redirect back to PayPal approval link.
        """
        order_data = self.get_order_details(order_id)

        if not order_data:
            logger.error(
                "No order data found for order_id {}".format(order_id))
            return {"status": "error", "message": "Order details not found"}

        status = order_data.get("status")

        if status == "APPROVED":
            update_data = {
                "status": PAYPAL_ORDER_STATUS_APPROVED
            }
            self.update_paypal_transaction_data(paypal_transaction,
                                                update_data)
            logger.info("Order is APPROVED for transaction {}".format(
                self.transaction_id))
            return {"status": PAYPAL_ORDER_STATUS_APPROVED}

        elif status == "CREATED":
            links = order_data.get("links", [])
            approval_url = None
            for link in links:
                if link.get("rel") == "approve":
                    approval_url = link.get("href")
                    break

            if approval_url:
                logger.error(
                    "Order is in CREATED state, redirecting back to PayPal approval page for transaction {}".format(
                        self.transaction_id))
                return {
                    "status": PAYPAL_ORDER_STATUS_CREATED,
                    "redirect_url": approval_url
                }
            else:
                logger.error(
                    "Approval URL not found in PayPal order response for transaction {}".format(
                        self.transaction_id))
                return {
                    "status": "error",
                    "message": "Approval link not found"
                }

        else:
            logger.error(
                "Order is not approved. Status: {} for transaction {}".format(
                    status, self.transaction_id))
            return {
                "status": "error",
                "message": "Order is not approved or ready"
            }
