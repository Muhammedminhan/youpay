from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.messages import ERROR_MESSAGE, ERROR_MISSING_FIELDS
from core.response_messages import YGPayResponse
from services.v1.serializers.payment_request import (
    PaymentRequestDataSerializer)
from services.v1.views.common import YGPayTransactionCRUD
from services.v1.views.utils import get_data_from_request
from ygpay.settings.base import REDIRECT_URL


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
            "invoice",
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

                transaction_response = self.store_ygpay_transaction_data(
                    request)
                if transaction_response['status'] == status.HTTP_201_CREATED:
                    redirect_url = REDIRECT_URL + "/{}{}".format(
                        "?id=",
                        transaction_response['data']['transaction_id'])

                    response_data = {
                        "status": status.HTTP_201_CREATED,
                        "message": "created",
                        "url": redirect_url
                    }
                    return Response(response_data,
                                    status=status.HTTP_201_CREATED)

                else:
                    data = self.get_error_dict(
                        error_code=self.UNKNOWN_ERR,
                        serializer_error=transaction_response['data']
                    )

                    return Response(data.get('errors'),
                                    status=status.HTTP_404_NOT_FOUND)
            else:
                errors = serializer.errors.keys()
                missing_fields = ', '.join(
                    ["".join(missing) for missing in errors])
                message = "{}{}".format(ERROR_MISSING_FIELDS, missing_fields)
                error_response = {
                    "status": status.HTTP_400_BAD_REQUEST,
                    'message': ERROR_MESSAGE,
                    'error': message,
                }
                return Response(error_response,
                                status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {'message': ERROR_MESSAGE, "error": str(e),
                 "status": status.HTTP_400_BAD_REQUEST},
                status=status.HTTP_400_BAD_REQUEST)
