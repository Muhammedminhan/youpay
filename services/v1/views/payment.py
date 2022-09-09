import logging

import requests
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.response_messages import YouPayResponse
from core.utils import encrypt_payment_data, decrypt_payment_data
from services.models import PaymentRequestData
from services.v1.serializers.payment_request import (
    PaymentRequestDataSerializer)
from services.v1.views.common import YouPayTransactionCRUD, ClientValidator
from services.v1.views.utils import (
    get_data_from_request,
    reformat_payment_request_data
)
from youpay.settings.base import PAYMENT_REDIRECT_URL

logger = logging.getLogger(__name__)


class PaymentRequestView(YouPayTransactionCRUD, APIView, ClientValidator):
    response_obj = YouPayResponse()
    """
    API endpoint that allows clients create payment request for products.
    """

    def get(self, request):

        data = {
            "payment": {
                "product_code": "",
                "payment_platform": "IOS",
                "ip": "192.168.1.1",
                "language": "en",
                "invoice_id": "1234",
                "order_reference": "Gift-1234-ecom"
            },
            "order": {
                "amount": 1000,
                "currency": "AED",
                "service_fee": 123,
                "base_amount": 2344,
                "VAT_amount": 13
            },
            "customer": {
                "email": "jomon@yougotagift.com",
                "phone": 12324234,
                "name": "jomon",
                "registered_since": "26-03-1994"
            },
            "order_history": {
                "total_items": 2,
                "items": [
                    {
                        "tittle": "item 1",
                        "category": "electronic-gift",
                        "ref_id": "item-123"
                    },
                    {
                        "tittle": "item 2",
                        "category": "electronic-gift",
                        "ref_id": "item-124"
                    },
                    {
                        "tittle": "item 3",
                        "category": "electronic-gift",
                        "ref_id": "item-125"
                    }
                ]
            },
            "order_items": {
                "items": [
                    {
                        "tittle": "item 1",
                        "category": "electronic-gift",
                        "ref_id": "item-123"
                    },
                    {
                        "tittle": "item 2",
                        "category": "electronic-gift",
                        "ref_id": "item-124"
                    },
                    {
                        "tittle": "item 3",
                        "category": "electronic-gift",
                        "ref_id": "item-125"
                    }
                ]
            },
            "session_id": "sessionid"
        }

        enc_data = encrypt_payment_data(data)
        print(enc_data)

        # send post request to payment
        url = "http://localhost:8000/services/api/v1/payment/"
        headers = {'x-api-key': 'eMck6LwBxlaYu6g0nNeNxBksRlEf0tAkHtD4NElA3pY',
                   'Content-Type': 'application/json'}
        response = requests.post(url, data=enc_data,
                                 headers=headers)
        return Response({
            "response": response.json()
        })

    def __init__(self):
        self.PAYMENT_REQUEST_DATA_FIELDS_LIST = [
            "request_data",
            "response_data",
            "amount",
            "currency",
            "invoice_id",
            "order_reference",
            "payment_reference",
            "platform",
            "customer_email",
            "customer_phone",
            "language",
            "session_id",
            "payment_status",
            "service_fee",
            "base_amount",
            "VAT_amount",
            "order_history",
            "ip",
        ]

        self.payment_request_obj = None
        self.return_data = None

    def post(self, request):
        try:
            decrypted_data = decrypt_payment_data(request.data)
            data_formatted = reformat_payment_request_data(decrypted_data)
            data = get_data_from_request(
                self.PAYMENT_REQUEST_DATA_FIELDS_LIST, data_formatted)

            validate, client_pk = self.validate_client(request)

            if validate is False:
                logger.info("payment request client validation failed for {0}"
                            .format("order_reference"))
                self.return_data = self.response_obj.get_400_message(
                    message="Client Does Not Exist")

                return Response(self.return_data.get('errors'),
                                status=status.HTTP_400_BAD_REQUEST)

            data['api_client'] = client_pk
            serializer = PaymentRequestDataSerializer(data=data)

            if PAYMENT_REDIRECT_URL is None or PAYMENT_REDIRECT_URL == "":
                """
                Transaction not created, payment url not configured
                """
                self.return_data = self.response_obj.get_400_message(
                    message="Please configure payment redirect url")

                return Response(self.return_data.get('errors'),
                                status=status.HTTP_400_BAD_REQUEST)

            if serializer.is_valid():
                self.payment_request_obj = serializer.save()
                transaction_response = self.create_youpay_transaction_data(
                    data)
                if transaction_response['status'] == status.HTTP_201_CREATED:
                    redirect_url = PAYMENT_REDIRECT_URL + "/{}{}".format(
                        "?transaction_id=",
                        transaction_response['data']['transaction_id'])

                    response_data = {
                        "status": status.HTTP_201_CREATED,
                        "message": "created",
                        "session_id": transaction_response['data'][
                            'session_id'],
                        "transaction_id": transaction_response['data'][
                            'transaction_id'],
                        "url": redirect_url
                    }

                    self.return_data = self.response_obj.get_success_dict(
                        code=self.response_obj.SUCCESS,
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
                    self.return_data = self.response_obj.get_400_message(
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
                self.return_data = self.response_obj.get_error_dict(
                    error_code=self.response_obj.UNKNOWN_ERR,
                    serializer_error=serializer.errors,
                )
                logger.error(
                    "Validation failed for PaymentRequestDataSerializer : {}"
                    .format(self.return_data))

                return Response(self.return_data.get('errors'),
                                status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            self.return_data = self.response_obj.get_400_message(
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
