import json
import logging
from datetime import datetime

import requests
from decouple import config
from rest_framework import status

from core.constants import (REQUEST_METHOD_POST, PAYMENT_GATEWAY_PAYPAL,
                            REQUEST_METHOD_PUT, REQUEST_METHOD_GET)
from core.utils import (get_payment_gateway_config, get_app_config,
                        get_redirect_url, wait_redis_lock)
from gateways.common import (_get_payment_reference_number, get_request_id,
                             unique_token_generator)
from gateways.paypal.constants import (PAYPAL_ORDER_STATUS_CREATED,
                                       PAYPAL_ORDER_ENDPOINT,
                                       PAYPAL_ORDER_STATUS_APPROVED,
                                       PAYPAL_CAPTURE_STATUS_COMPLETED,
                                       PAYPAL_CAPTURE_FAILURE_REASON_MAPPING,
                                       PAYPAL_CAPTURE_STATUS_FAILED,
                                       PAYPAL_STC_ENDPOINT,
                                       PAYPAL_REFUND_STATUS_COMPLETED,
                                       PAYPAL_REFUND_ENDPOINT,
                                       PAYPAL_RESPONSE_COMPLETE_STATUS)
from gateways.paypal.models import PaymentAccessToken, PaypalTransaction
from integrations.constants import (PAYMENT_REQUEST_TYPE_CREATE_ORDER,
                                    PAYMENT_REQUEST_TYPE_CAPTURE_ORDER,
                                    PAYPAL_HUB_CODE, PAYPAL_CACHE_KEY,
                                    PAYMENT_REQUEST_TYPE_SET_TRANSACTION_CONTEXT,
                                    PAYMENT_REQUEST_TYPE_ORDER_STATUS)
from payments.constants import (PAYMENT_METHOD_PAYPAL, PAYMENT_STATUS_PENDING,
                                PAYMENT_STATUS_PAID, PAYMENT_STATUS_FAILED,
                                PAYMENT_STATUS_REFUNDED)
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
        self.sender_youpay_account_id = None
        self.tracking_id_stc = None

    def set_paypal_stc_context(self, access_token, request_data):
        """
       Sets the PayPal STC (Set Transaction Context) to provide buyer info for risk evaluation.

       Sends sender details like name, email, phone, and country to PayPal to bind with
       future order and capture requests using a tracking ID.

       :param access_token: PayPal access token, PayPal-Request-Id
       :param request_data: Data containing sender (payer) details
       :return: True if STC was set successfully, else False
       """
        try:
            logger.info(
                "Setting paypal stc context for transaction id: {}".format(
                    self.transaction_id))

            headers = {
                'Authorization': access_token,
                'Content-Type': 'application/json',
                'PayPal-Request-Id': get_request_id()
            }

            self.sender_youpay_account_id = unique_token_generator(size=15)
            self.tracking_id_stc = unique_token_generator(size=15)

            payload = {
                "additional_data": [
                    {"key": "sender_account_id",
                     "value": self.sender_youpay_account_id},
                    {"key": "sender_first_name",
                     "value": request_data.get("payment_source", {}).get(
                         "paypal",
                         {}).get(
                         "name", {}).get("given_name", "")},
                    {"key": "sender_last_name",
                     "value": request_data.get("payment_source", {}).get(
                         "paypal",
                         {}).get(
                         "name", {}).get("surname", "")},
                    {"key": "sender_email",
                     "value": request_data.get("payment_source", {}).get(
                         "paypal",
                         {}).get(
                         "email_address", "")},
                    {"key": "sender_phone",
                     "value": self.request_data.get("customer_phone", "")},
                    {"key": "sender_country_code",
                     "value": self.request_data.get("country_code", "")},
                    {"key": "sender_create_date",
                     "value": datetime.utcnow().isoformat() + "Z"}
                ]
            }
            merchant_id = config("PAYPAL_MERCHANT_ID")

            url = self.paypal_config.domain + PAYPAL_STC_ENDPOINT + f"{merchant_id}/{self.tracking_id_stc}"

            response = requests.put(
                url,
                headers=headers,
                json=payload
            )

            self.create_youpay_to_payment_gateways_data(
                transaction_obj=self.transaction_obj,
                transaction_id=self.transaction_id,
                request_data=json.dumps(payload),
                response_data=response.text if response.text else "{}",
                request_method=REQUEST_METHOD_PUT,
                request_type=PAYMENT_REQUEST_TYPE_SET_TRANSACTION_CONTEXT,
            )

            if response.status_code == status.HTTP_200_OK:
                return True
            logger.error(
                "Unable to create payment transaction context for transaction id: {}".format(
                    self.transaction_id))
            return False

        except Exception as e:
            logger.error(
                "Exception occurred while setting paypal stc context",
                exc_info=True)
            return False

    def create_order(self, request_data):
        """
        Initiates a PayPal order after verifying the YouPay transaction.
        Handles STC (Set Transaction Context), creates the order, and logs all details.

        :param request_data: Dictionary with transaction_id, order_reference, etc.
        :return: Tuple (response_data, status_code)
        """
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
                access_token = headers.get('Authorization')
                paypal_client_metadata_id = self.set_paypal_stc_context(
                    access_token, payload)
                headers.update({
                    "PayPal-Client-Metadata-Id": self.tracking_id_stc
                })
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
        """
        Prepares the payload with structure needed for the PayPal create order.
        """
        customer_name = self.request_data.get('customer_name', '')
        name_parts = customer_name.strip().split()
        app_config = get_app_config()
        params = '?id=' + self.request_data.get('encrypted_transaction_id')

        return_url = add_payment_gateway_info_in_url(
            transaction_data=self.request_data,
            app_config=app_config, params=params,
            code=PAYPAL_HUB_CODE)

        redirect_url = get_payment_redirect_url()
        cancel_url = redirect_url + "{}/{}".format(
            self.transaction_obj.language,
            self.request_data.get('encrypted_transaction_id'))
        experience_context = {
            "return_url": return_url,
            "cancel_url": cancel_url
        }

        payment_source = {
            "paypal": {
                'name': {
                    'given_name': name_parts[0] if len(
                        name_parts) > 0 else '',
                    'surname': name_parts[1] if len(name_parts) > 1 else '',
                },
                'email_address': self.request_data.get('customer_email'),
                'experience_context': experience_context,
            }
        }
        self.reference_id = _get_payment_reference_number(
            self.order_reference)

        purchase_units = [{
            "invoice_id": self.reference_id,
            "amount": {
                "breakdown": {
                    "item_total": {
                        "currency_code": self.request_data.get('currency'),
                        "value": float(
                            self.request_data.get('additional_total_amount')),
                    }
                },
                "currency_code": self.request_data.get('currency'),
                "value": float(
                    self.request_data.get('additional_total_amount')),
            },
            "items": [
                {
                    "description": "Gift cards",
                    "name": "Digital gift cards",
                    "quantity": "1",
                    "unit_amount": {
                        "currency_code": self.request_data.get('currency'),
                        "value": float(
                            self.request_data.get('additional_total_amount'))
                    },
                    "category": "DIGITAL_GOODS"
                }
            ]
        }]

        request_data = {
            'payment_source': payment_source,
            'intent': 'CAPTURE',
            'purchase_units': purchase_units,
        }

        return request_data

    def handle_paypal_order_response(self, response_data, payment_data):
        """
        Handles the response from PayPal's Create Order API.

        If the status is 'PAYER_ACTION_REQUIRED' and redirect URL is found,
        it updates YouPay transaction data and creates a PaypalTransaction entry.

        :param response_data: The JSON response from PayPal.
        :param payment_data: The data used in the original order request.
        :return: Tuple of (response_dict, HTTP status code)
        """
        status = response_data.get("status")
        order_id = response_data.get("id")
        links = response_data.get("links", [])
        redirect_url = None

        for link in links:
            if link.get("rel") == "payer-action":
                redirect_url = link.get("href")
                break

        if status == "PAYER_ACTION_REQUIRED" and redirect_url:
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
        """
        Prepares the authorization and content headers for PayPal API requests.

        :return: Dictionary of headers
        """
        gateway_obj = self.paypal_config
        access_token = PaymentAccessToken.get_paypal_access_token(gateway_obj)
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}',
        }
        return headers

    def prepare_data_to_update(self, response_data):
        """
        Prepares a dictionary of fields to update the YouPayTransaction table.

        :param response_data: The PayPal Create Order API response.
        :return: Dictionary of data to update
        """
        data_to_update = {
            'transaction_id': self.transaction_id,
            "payment_status": self.payment_status,
            "payment_reference": self.reference_id,
            "payment_method": self.payment_method,
            "payment_gateway": self.payment_gateway,
            "additional_total_amount": self.request_data.get(
                'additional_total_amount'),
            "additional_vat": self.request_data.get('additional_vat'),
            "additional_processing_fee": self.request_data.get(
                'additional_processing_fee'),
            "additional_processing_fee_vat": self.request_data.get(
                'additional_processing_fee_vat'),
        }

        return data_to_update

    def create_paypal_transaction(self, response_data):
        """
        Creates paypal transaction entry
        """
        try:
            lock_name = ('lock:PaymentRequestView:reference_id%s'
                         % (self.reference_id,))
            with wait_redis_lock(lock_name=lock_name):
                data = {
                    "order_id": response_data.get('id'),
                    "payment_reference": self.reference_id,
                    "status": PAYPAL_ORDER_STATUS_CREATED,
                    "amount": self.request_data.get(
                        'additional_total_amount'),
                    "currency": self.request_data.get('currency'),
                    "customer_name": self.request_data.get('customer_name'),
                    "customer_email": self.request_data.get('customer_email'),
                    "customer_phone": self.request_data.get('customer_phone'),
                    "sender_youpay_account_id": self.sender_youpay_account_id,
                    "tracking_id_stc": self.tracking_id_stc,
                    "youpay_transaction_id": self.transaction_id,
                }
                PaypalTransaction.objects.create(**data)

        except Exception as e:
            logger.error(
                "Exception while creating paypal transaction for {}: {}".format(
                    e, self.transaction_id))

    def capture_paypal_order(self, request_data):
        """
        Captures a PayPal order after checking if it's approved.
        Handles order status checking and logs all details.

        :param request_data: Dictionary with transaction_id, order_reference, etc.
        :return: Tuple (response_data, status_code)
        """
        try:
            self.transaction_id = request_data.get('transaction_id')
            self.transaction_obj = request_data.get('transaction_obj')
            self.reference_id = self.transaction_obj.payment_reference
            order_id = request_data.get('order_id')
            self.order_id = order_id
            headers = self.get_headers()
            paypal_transaction = self.get_paypal_transaction()
            self.tracking_id_stc = paypal_transaction.tracking_id_stc
            headers.update({
                "PayPal-Client-Metadata-Id": self.tracking_id_stc
            })
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
                else:
                    response_data, response_code = self.handle_paypal_capture_failure(
                        paypal_transaction, response
                    )

                return response_data, response_code
            elif order_status["status"] == PAYPAL_ORDER_STATUS_CREATED:

                return_data = {
                    "status": 200,
                    "is_redirect": True,
                    "redirect_url": order_status["redirect_url"],
                    "is_success": False,
                    "message": "Paypal Payment Not Complete",
                }
                return return_data, self.PAYPAL_PAYMENT_INCOMPLETE
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
                "Paypal capturing order connection error for transaction id {}"
                " with error {}".format(self.transaction_id, connection_err))
            return None, self.PAYPAL_CONNECTION_ERROR
        except Exception as e:
            logger.error(
                "Exception while capturing order for {} with error: {}".format(
                    self.transaction_id, e))
            return None, self.PAYPAL_CONNECTION_ERROR

    def get_paypal_transaction(self):
        """
        Get paypal transaction object with reference id and order id
        """
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
        """
        Handles the response from PayPal's Capture Order API.

        If the status is Completed and redirect URL is found,
        it updates YouPay transaction data as paid and  PaypalTransaction as
        capture completed, else mark as failed and redirect it to failure page

        :param response_data: The JSON response from PayPal.
        :param payment_data: The data used in the original order request.
        :return: Tuple of (response_dict, HTTP status code)
        """
        try:
            status = paypal_transaction.status
            purchase_unit = response_data_json.get("purchase_units", [{}])[0]
            captures = purchase_unit.get("payments", {}).get("captures", [])
            capture = captures[0]
            capture_status = capture.get("status", "").upper()
            if capture_status == PAYPAL_RESPONSE_COMPLETE_STATUS:
                redirect_url = get_redirect_url(
                    self.transaction_obj.success_url,
                    self.transaction_id)
                return_data = {
                    "status": 200,
                    "is_redirect": True,
                    "redirect_url": redirect_url,
                    "is_success": True,
                }
                code = self.SUCCESS
                status = PAYPAL_CAPTURE_STATUS_COMPLETED
                response_data_json[
                    'success'] = PAYPAL_CAPTURE_STATUS_COMPLETED
                youpay_update_data = {
                    "transaction_id": self.transaction_id,
                    "payment_status": PAYMENT_STATUS_PAID
                }
            else:
                logger.error(
                    "paypal capture response status is not COMPLETED for {}".format(
                        self.transaction_id))
                redirect_url = get_redirect_url(
                    self.transaction_obj.failure_url,
                    self.transaction_id)
                return_data = {
                    "status": 400,
                    "is_redirect": True,
                    "redirect_url": redirect_url,
                    "is_success": False,
                }
                youpay_update_data = {
                    "transaction_id": self.transaction_id,
                    "payment_status": PAYMENT_STATUS_FAILED
                }
                code = self.PAYPAL_CONNECTION_ERROR

            self.update_youpay_transaction_data(youpay_update_data)
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

    def handle_paypal_capture_failure(self, paypal_transaction,
                                      response, ):
        """
        Handles a failed PayPal capture attempt:
        - Updates transaction record with failure details.
        - Logs and returns failure url.
        """
        try:
            response_json = response.json()
        except ValueError:
            response_json = {
                "message": "Unexpected error format from PayPal",
                "raw_text": response.text
            }

        issue = None
        description = None
        debug_id = response_json.get("debug_id")
        message = response_json.get("message")

        if message:
            readable_reason = message
        else:
            issue = response_json["details"][0].get("issue")
            readable_reason = PAYPAL_CAPTURE_FAILURE_REASON_MAPPING.get(
                issue, )

        logger.error(
            f"PayPal capture failed [order_id={paypal_transaction.order_id}]: "
            f"Issue={issue}, Description={description}, DebugID={debug_id}"
        )

        paypal_transaction.status = PAYPAL_CAPTURE_STATUS_FAILED
        paypal_transaction.error_message = readable_reason
        paypal_transaction.debug_id = debug_id
        paypal_transaction.save(update_fields=[
            "status", "error_message", 'debug_id'
        ])
        redirect_url = get_redirect_url(self.transaction_obj.failure_url,
                                        self.transaction_id)

        response_data = {
            'is_redirect': True,
            'redirect_url': redirect_url,
            'is_success': False,
            'message': readable_reason,
        }

        self.update_youpay_transaction_data({
            'transaction_id': self.transaction_id,
            'payment_status': PAYMENT_STATUS_FAILED

        })

        return response_data, self.PAYPAL_CONNECTION_ERROR

    def update_paypal_transaction_data(self, paypal_transaction,
                                                    response_data):
        """Method to update paypal transaction data"""

        data_dict = {}
        try:
            purchase_unit = response_data.get("purchase_units", [{}])[0]
            capture_info = (
                purchase_unit.get("payments", {}).get("captures", [{}])[0])
            payer = response_data.get("payer", {})
            seller_receivable = None

            if capture_info:
                data_dict["capture_id"] = capture_info.get("id")
                seller_receivable = capture_info.get(
                    "seller_receivable_breakdown", {})

            if seller_receivable:
                data_dict["net_amount"] = seller_receivable.get(
                    "net_amount").get(
                    "value")
                data_dict["paypal_fee"] = seller_receivable.get(
                    "paypal_fee").get(
                    "value")
                data_dict["receivable_amount"] = seller_receivable.get(
                    "receivable_amount").get("value")
                data_dict[
                    "receivable_amount_currency_code"] = seller_receivable.get(
                    "receivable_amount").get("currency_code")
                data_dict["source_currency"] = seller_receivable.get(
                    "exchange_rate").get("source_currency")
                data_dict["exchange_rate"] = seller_receivable.get(
                    "exchange_rate").get("value")
                data_dict["target_currency"] = seller_receivable.get(
                    "exchange_rate").get("target_currency")

            if payer:
                data_dict["customer_email"] = payer.get("email_address")
                data_dict["payer_id"] = payer.get("payer_id")
                name_data = payer.get("name", {})
                data_dict[
                    "customer_name"] = (f"{name_data.get('given_name', '')} "
                                        f"{name_data.get('surname', '')}").strip()

            data_dict["status"] = response_data.get("status")
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
        """
        Call PayPal Show Order Details API to get current status of the order
        """
        try:
            url = self.paypal_config.domain + PAYPAL_ORDER_ENDPOINT + '/' + order_id
            headers = self.get_headers()
            response = requests.get(url, headers=headers)
            logger.info("Show order details for transaction {}, {}"
                        "".format(response.text, self.transaction_id))

            self.create_youpay_to_payment_gateways_data(
                transaction_obj=self.transaction_obj,
                transaction_id=self.transaction_id,
                request_data=json.dumps({}),
                response_data=response.text,
                request_method=REQUEST_METHOD_GET,
                request_type=PAYMENT_REQUEST_TYPE_ORDER_STATUS,
            )

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
                    "Order is in CREATED state, redirecting back to PayPal "
                    "approval page for transaction {}".format(
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

    def refund_paypal_transaction(self, request_data):
        self.reference_id = request_data.get("payment_reference")
        self.transaction_id = request_data.get("transaction_id")
        self.transaction_obj = request_data.get("transaction_obj")
        paypal_transaction = self.get_paypal_transaction()
        capture_id = paypal_transaction.capture_id
        self.paypal_transaction = paypal_transaction

        try:
            headers = self.get_headers()
            url = self.paypal_config.domain + PAYPAL_REFUND_ENDPOINT + capture_id + "/refund"
            payload = {
                "amount": {
                    "value": str(
                        self.transaction_obj.additional_total_amount),
                    "currency_code": self.transaction_obj.currency
                },
                "invoice_id": str(self.transaction_obj.invoice_id),
                "note": "Defective product"
            }

            response = requests.post(
                url,
                headers=headers,
                data=json.dumps(payload)
            )
            logger.info("Paypal refund order response for {}: {}".format(
                self.transaction_id, response.text))

            self.create_youpay_to_payment_gateways_data(
                transaction_obj=self.transaction_obj,
                transaction_id=self.transaction_id,
                request_data=json.dumps(payload),
                response_data=response.text,
                request_method=REQUEST_METHOD_POST,
                request_type=PAYMENT_REQUEST_TYPE_CAPTURE_ORDER,
            )

            if response:
                response_data_json = response.json()
                response_data, response_code = self.handle_paypal_refund_response(
                    response_data_json)
                return response_data, response_code


        except requests.ConnectTimeout as timeout_err:
            logger.error(
                "Paypal refund order request timeout for transaction "
                "{} with error {}".format(
                    self.transaction_id, timeout_err))
            return None, timeout_err
        except requests.ConnectionError as connection_err:
            logger.error(
                "Paypal refund order connection error for transaction id {} with error {}".format(
                    self.transaction_id, connection_err))
            return None, self.PAYPAL_CONNECTION_ERROR
        except Exception as e:
            logger.error(
                "Exception while refunding order for {} with error: {}".format(
                    self.transaction_id, e))
            return None, self.PAYPAL_CONNECTION_ERROR

    def handle_paypal_refund_response(self, response_data_json):
        status = response_data_json.get("status")
        if status == PAYPAL_RESPONSE_COMPLETE_STATUS:
            refund_update_data = {
                "refund_id": response_data_json.get("id"),
                "status": PAYPAL_REFUND_STATUS_COMPLETED
            }
            self.update_youpay_transaction_data(
                {'transaction_id': self.transaction_id,
                 'payment_status': PAYMENT_STATUS_REFUNDED})
            self.update_paypal_transaction_data(
                self.paypal_transaction,
                refund_update_data)
            return response_data_json, self.SUCCESS
        else:
            logger.error(
                f"Refund failed for capture {response_data_json}")
            return {"error": "Refund failed"}, self.PAYPAL_CONNECTION_ERROR
