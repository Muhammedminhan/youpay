from decouple import config
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.response_messages import YGPayResponse
from services.v1.serializers.payment_request import (
    PaymentRequestDataSerializer)
from services.v1.views.common import YGPayTransactionCRUD
from services.v1.views.utils import get_data_from_request


class PaymentRequestView(YGPayTransactionCRUD, APIView):
    response_obj = YGPayResponse()
    """
    API endpoint that allows clients create payment request for products.
    """

    def __init__(self):
        self.PAYMENT_REQUEST_DATA_FIELDS_LIST = [
            "request_data",
            "response_data",
            "amount",
            "currency",
            "api_client",
            "invoice_id",
            "order_reference",
            "payment_reference",
            "platform",
            "customer_email",
            "customer_phone",
            "language",
        ]

    def post(self, request):
        try:
            data = get_data_from_request(
                self.PAYMENT_REQUEST_DATA_FIELDS_LIST, request.data)
            serializer = PaymentRequestDataSerializer(data=data)
            if serializer.is_valid():
                serializer.save()

                transaction_response = self.create_ygpay_transaction_data(
                    request)
                if transaction_response['status'] == status.HTTP_201_CREATED:
                    redirect_url = config(
                        "PAYMENT_REDIRECT_URL",
                        "http://localhost:3000") + "/{}{}".format(
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

                    data = self.response_obj.get_success_dict(
                        code=self.response_obj.SUCCESS,
                        success_dict=response_data
                    )
                    return Response(data, status=status.HTTP_201_CREATED)

                else:
                    """
                    Transaction not created 
                    """
                    data = self.response_obj.get_400_message(
                        message=transaction_response["message"],
                    )

                    return Response(data.get('errors'),
                                    status=status.HTTP_400_BAD_REQUEST)
            else:
                """
                PaymentRequestDataSerializer validation failed
                """
                data = self.response_obj.get_error_dict(
                    error_code=self.response_obj.UNKNOWN_ERR,
                    serializer_error=serializer.errors,
                )

                return Response(data.get('errors'),
                                status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            data = self.response_obj.get_400_message(
                message={"error": str(e)},
            )

            return Response(data, status=status.HTTP_400_BAD_REQUEST)
