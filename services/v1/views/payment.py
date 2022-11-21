import json
import logging

import requests
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.messages import PAYMENT_REQUEST_KEYS_ERROR, REDIRECT_URL
from core.response_messages import YouPayResponse
from core.utils import (encrypt_payment_data, decrypt_payment_data,
                        encrypt_string, decrypt_string)
from payments.constants import PAYMENT_STATUS_CANCELLED
from services.models import PaymentRequestData
from services.utils import get_payment_redirect_url
from services.v1.serializers.payment_request import (
    PaymentRequestDataSerializer, PaymentVerifyDataSerializer)
from services.v1.views.common import YouPayTransactionCRUD, ClientValidator
from services.v1.views.utils import (
    reformat_payment_request_data
)

logger = logging.getLogger(__name__)


class PaymentRequestView(YouPayTransactionCRUD, APIView, ClientValidator,
                         YouPayResponse):
    """
    API endpoint that allows clients create payment request for products.
    """

    def __init__(self):
        self.payment_request_obj = None
        self.return_data = None

    def post(self, request):
        """
        decrypted_data : stores the decrypted data from request

        data_formatted : stores the formatted data from decrypted_data, ie
        data with keys as fields in PaymentRequestData table

        """
        try:
            # Validate client at first
            validate, client_pk = self.validate_client(request)
            if not validate:
                logger.info(
                    "payment request client validation failed for {0}"
                    .format("order_reference"))
                self.return_data = self.get_400_message(
                    message="Client Does Not Exist")
                return Response(self.return_data.get('errors'),
                                status=status.HTTP_400_BAD_REQUEST)

            decrypted_data = decrypt_payment_data(request.data)
            data_formatted = reformat_payment_request_data(decrypted_data)

            if not data_formatted:
                """
                Decrypted data is empty or does not contain required keys
                """
                message = PAYMENT_REQUEST_KEYS_ERROR
                self.return_data = self.get_400_message(
                    message=message)
                return Response(self.return_data.get('errors'),
                                status=status.HTTP_400_BAD_REQUEST)

            data_formatted['api_client'] = client_pk
            serializer = PaymentRequestDataSerializer(data=data_formatted)

            PAYMENT_REDIRECT_URL = get_payment_redirect_url()
            if PAYMENT_REDIRECT_URL is None or PAYMENT_REDIRECT_URL == "":
                """
                Transaction not created, payment url not configured
                """
                self.return_data = self.get_400_message(
                    message="Please configure payment redirect url")

                return Response(self.return_data.get('errors'),
                                status=status.HTTP_400_BAD_REQUEST)

            if serializer.is_valid():
                self.payment_request_obj = serializer.save()
                transaction_response = self.create_youpay_transaction_data(
                    data_formatted)
                if transaction_response['status'] == status.HTTP_201_CREATED:

                    encrypted_transaction_id = encrypt_string(
                        transaction_response['data'][
                            'transaction_id'])

                    redirect_url = PAYMENT_REDIRECT_URL + "/{}".format(
                        encrypted_transaction_id)

                    response_data = {
                        "status": status.HTTP_201_CREATED,
                        "message": "created",
                        "url": redirect_url
                    }
                    self.return_data = self.get_success_dict(
                        code=self.SUCCESS,
                        success_dict=response_data
                    )
                    self.save_response_data(self.payment_request_obj,
                                            self.return_data)
                    return Response(self.return_data,
                                    status=status.HTTP_201_CREATED)

                else:
                    """
                    Transaction not created 
                    """
                    self.return_data = self.get_400_message(
                        message=transaction_response["message"],
                    )
                    logger.error(
                        "Error in creating transaction : {}".format(
                            transaction_response["message"]))

                    self.save_response_data(self.payment_request_obj,
                                            self.return_data)

                    return Response(self.return_data.get('errors'),
                                    status=status.HTTP_400_BAD_REQUEST)
            else:
                """
                PaymentRequestDataSerializer validation failed
                """
                self.return_data = self.get_error_dict(
                    error_code=self.UNKNOWN_ERR,
                    serializer_error=serializer.errors,
                )
                logger.error(
                    "Validation failed for PaymentRequestDataSerializer : {}"
                    .format(self.return_data))

                return Response(self.return_data.get('errors'),
                                status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            import sys, os
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            logger.error("Exception in payment request : {} {} {}"
                         .format(exc_type, fname, exc_tb.tb_lineno))
            logger.error("Exception in payment request : {} "
                         .format(e))
            self.return_data = self.get_400_message(
                message={"error": str(e)},
            )

            if self.payment_request_obj is not None:
                '''Save response data to PaymentRequestData table'''
                self.save_response_data(self.payment_request_obj,
                                        self.return_data)

            logger.error("Error in creating payment request : {}".format(e))
            return Response(self.return_data,
                            status=status.HTTP_400_BAD_REQUEST)
        finally:
            logger.info(
                "Payment request completed : {}".format(self.return_data))

    def save_response_data(self, payment_request_obj, response_data):
        """
        Save response data to PaymentRequestData table
        """
        try:
            PaymentRequestData.objects.filter(
                id=payment_request_obj.id).update(response_data=response_data)
        except Exception as e:
            logger.error("Error in saving response data for : {}".format(e))

    def verify_transaction(self, data):
        serializer = PaymentVerifyDataSerializer(data=data)
        if serializer.is_valid():
            """Validate transaction data with youpay client"""
            transaction_id = serializer.validated_data.get(
                'transaction_id')
            transaction_obj = self.get_youpay_transaction_data(
                transaction_id)

            if transaction_obj.api_client is None:
                """Client does not exist"""
                return_data = self.get_400_message(
                    message="API Client Does Not Exist or Inactive")
                return return_data, status.HTTP_400_BAD_REQUEST

            if transaction_obj.api_client.is_active is False:
                '''Skip verification if client is inactive'''
                dummy_response = {
                    "is_verified": True,
                }
                logger.info(
                    "Client is inactive, skipping verification for "
                    "transaction : {}".format(transaction_id))

                return dummy_response, status.HTTP_200_OK

            client_verify_url = transaction_obj.verify_url
            if client_verify_url is None or client_verify_url == "":
                return_data = self.get_400_message(
                    message="Please configure client verify url")
                return return_data, status.HTTP_400_BAD_REQUEST
            else:
                """
                Verify transaction with client by calling verify url
                """
                verify_body = {
                    "transaction_id": str(transaction_obj.transaction_id),
                    "invoice_id": transaction_obj.invoice_id,
                    "amount": str(transaction_obj.amount),
                    "currency": transaction_obj.currency,
                }

                response = self.verify_transaction_with_client(
                    client_verify_url, json.dumps(verify_body))
                logger.info("Client verify request send data : {}\nresponse "
                            "data{}".format(verify_body, response.text))

                if response:
                    return_data = self.get_success_dict(
                        code=self.SUCCESS,
                        success_dict=response.json()
                    )
                    return return_data, status.HTTP_200_OK
                else:
                    """Client verify url not responding"""
                    return_data = self.get_400_message(
                        message="Client verify url not working")
                    return return_data, status.HTTP_400_BAD_REQUEST

        else:
            response_data = self.get_error_dict(
                error_code=self.UNKNOWN_ERR,
                serializer_error=serializer.errors,
            )
            return response_data.get('errors'), status.HTTP_400_BAD_REQUEST

    def verify_transaction_with_client(self, client_verify_url, data):
        headers = {
            'Accept': 'application/json',
        }

        response = requests.post(client_verify_url, json=data,
                                 headers=headers)
        logger.info("Verify client with data {} ,Response {}".format(
            data, response.text))
        return response


class TestPaymentRequestView(YouPayTransactionCRUD, APIView, ClientValidator):
    """
    Test API endpoint for encrypting request data
    """

    def post(self, request):
        data = self.request.data
        enc_data = eval(encrypt_payment_data(data))
        return Response({
            "response": enc_data,
        })


class PaymentCancelledView(YouPayTransactionCRUD, APIView, ClientValidator):
    def post(self, request):
        try:
            logger.info("Triggered PaymentCancelledView")
            data = self.request.data
            transaction_id = decrypt_string(data.get('transaction_id'))
            transaction_object = self.get_youpay_transaction_data(
                transaction_id)
            self.update_youpay_transaction_data({
                'transaction_id': transaction_id,
                'payment_status': PAYMENT_STATUS_CANCELLED
            })

            redirect_url = (transaction_object.cancel_url +
                            '?transaction_id=' + transaction_id)
            logger.info(
                "Payment cancelled for transaction_id : {}, order reference :"
                "{}".format(transaction_id,
                            transaction_object.order_reference))
            return Response({
                REDIRECT_URL: redirect_url,
            })
        except Exception as e:
            logger.error("Error in payment cancel api  : {}".format(e))
            return Response({
                "error": str(e),
            })
