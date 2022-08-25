from django.http.response import Http404
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from core.messages import ERROR_MESSAGE, ERROR_MISSING_FIELDS
from services.models import APIClient, PaymentRequestData
from services.v1.views.serializers import APIClientRegistrationSerializer, \
    PaymentRequestDataSerializer


class APIClientRegistrationView(ListAPIView):
    """
    API endpoint that allows clients to view, create, update and delete.
    """

    queryset = APIClient.objects.all()
    serializer_class = APIClientRegistrationSerializer

    def get(self, request, pk=None):
        try:
            if pk:
                data = self.get_object(pk)
                serializer = APIClientRegistrationSerializer(data)

            else:
                data = APIClient.objects.all()
                serializer = APIClientRegistrationSerializer(data, many=True)

            return Response(serializer.data)
        except Http404:
            return Response({"message": "Data not found",
                             "status": status.HTTP_400_BAD_REQUEST},
                            status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"message": str(e),
                             "status": status.HTTP_400_BAD_REQUEST},
                            status=status.HTTP_400_BAD_REQUEST)

    def get_object(self, pk=None):
        try:
            return self.queryset.get(id=pk)
        except APIClient.DoesNotExist:
            raise Http404

    def post(self, request):
        try:
            api_client_id = request.data.get('id', None)
            if api_client_id:
                # Update API Client
                api_client_obj = APIClient.objects.get(id=api_client_id)
                serializer = APIClientRegistrationSerializer(
                    api_client_obj, data=request.data)
            else:
                # Create API Client
                serializer = APIClientRegistrationSerializer(
                    data=request.data)
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

    def delete(self, request, pk=None):
        try:
            if pk:
                APIClient.objects.filter(id=pk).delete()
                return Response({'message': "deleted data with id {}".format(
                    str(pk)), "status": status.HTTP_200_OK},
                    status=status.HTTP_200_OK)
            else:
                return Response({'message': ERROR_MESSAGE,
                                 'error': "No id provided in url",
                                 "status": status.HTTP_400_BAD_REQUEST},
                                status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'message': ERROR_MESSAGE, "error": str(e),
                             "status": status.HTTP_400_BAD_REQUEST},
                            status=status.HTTP_400_BAD_REQUEST)


class PaymentRequestView(ListAPIView):
    """
    API endpoint that allows clients create payment request for products.
    """

    queryset = PaymentRequestData.objects.all()
    serializer_class = PaymentRequestDataSerializer

    def post(self, request):
        try:
            data = {
                "request_data": self.request.data,
                "response_data": None,
                "amount": self.request.data['amount'],
                "currency": self.request.data['currency'],
                "api_client": self.request.data['api_client'],
                "invoice": self.request.data['invoice'],
                "order_reference": self.request.data['order_reference'],
                "payment_reference": self.request.data['payment_reference'],
                "platform": self.request.data['platform'],
                "customer_email": self.request.data['customer_email'],
                "customer_phone": self.request.data['customer_phone'],
                "language": self.request.data['language'],
            }

            # Create Payment Request
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
