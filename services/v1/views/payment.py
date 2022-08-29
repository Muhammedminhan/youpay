from django.http.response import Http404
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from core.messages import ERROR_MESSAGE, ERROR_MISSING_FIELDS
from services.v1.views.utils import get_data_from_request
from services.v1.serializers.payment_request import (
    PaymentRequestDataSerializer)


class PaymentRequestView(ListAPIView):
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
                return Response({"status": status.HTTP_201_CREATED,
                                 "data": serializer.data, "message": "created"
                                 }, status=status.HTTP_201_CREATED)
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
