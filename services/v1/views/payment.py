import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.response_messages import YouPayResponse
from core.utils import encrypt_payment_data, decrypt_payment_data
from services.models import PaymentRequestData
from services.utils import get_payment_redirect_url
from services.v1.serializers.payment_request import (
    PaymentRequestDataSerializer)
from services.v1.views.common import YouPayTransactionCRUD, ClientValidator
from services.v1.views.utils import (
    reformat_payment_request_data
)

logger = logging.getLogger(__name__)


class PaymentRequestView(YouPayTransactionCRUD, APIView, ClientValidator):
    response_obj = YouPayResponse()
    """
    API endpoint that allows clients create payment request for products.
    """

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
            "customer_name",
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
        """
        decrypted_data : stores the decrypted data from request

        data_formatted : stores the formatted data from decrypted_data, ie
        data with keys as fields in PaymentRequestData table

        """
        try:
            decrypted_data = decrypt_payment_data(request.data)
            data_formatted = reformat_payment_request_data(decrypted_data)

            if not data_formatted:
                """
                Decrypted data is empty
                """
                message = (
                    "payment request data is not in proper format, one of the"
                    " data is missing ie order or payment or customer")
                self.return_data = self.response_obj.get_400_message(
                    message=message)
                return Response(self.return_data.get('errors'),
                                status=status.HTTP_400_BAD_REQUEST)

            validate, client_pk = self.validate_client(request)

            if validate is False:
                logger.info(
                    "payment request client validation failed for {0}"
                    .format("order_reference"))
                self.return_data = self.response_obj.get_400_message(
                    message="Client Does Not Exist")
                return Response(self.return_data.get('errors'),
                                status=status.HTTP_400_BAD_REQUEST)

            data_formatted['api_client'] = client_pk
            serializer = PaymentRequestDataSerializer(data=data_formatted)

            PAYMENT_REDIRECT_URL = get_payment_redirect_url()
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
                    data_formatted)
                if transaction_response[
                    'status'] == status.HTTP_201_CREATED:
                    redirect_url = PAYMENT_REDIRECT_URL + "/{}{}".format(
                        "?transaction_id=",
                        transaction_response['data']['transaction_id'])

                    response_data = {
                        "status": status.HTTP_201_CREATED,
                        "message": "created",
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
            logger.error("Exception in payment request : {} "
                         .format(e))
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


class TestPaymentRequestView(YouPayTransactionCRUD, APIView, ClientValidator):
    response_obj = YouPayResponse()
    """
    Test API endpoint for encrypting request data
    """

    def post(self, request):
        data = self.request.data
        enc_data = eval(encrypt_payment_data(data))
        return Response({
            "response": enc_data,
        })
