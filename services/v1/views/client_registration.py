from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from core.messages import ERROR_MESSAGE, ERROR_MISSING_FIELDS
from services.models import APIClient
from services.v1.serializers.client_registrattion import (
    APIClientRegistrationSerializer)


class APIClientRegistrationViewSet(ViewSet):
    """
    API endpoint that allows clients to view, create, update and delete
    and store response
    """

    serializer_class = APIClientRegistrationSerializer

    def list(self, request):
        queryset = APIClient.objects.all()
        serializer = APIClientRegistrationSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        queryset = APIClient.objects.all()

        api_client_qs = get_object_or_404(queryset, pk=pk)
        serializer = APIClientRegistrationSerializer(api_client_qs)
        return Response(serializer.data)

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
