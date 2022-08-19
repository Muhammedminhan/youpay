from django.http.response import Http404
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from services.models import APIClient
from services.v1.views.serializers import APIClientRegistrationSerializer


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
                message = "The following fields are missing or incorrect " \
                          "value provided : {}".format(missing_fields)
                error_response = {
                    'message': "One of the required fields is missing "
                               "or request is not formatted correctly",
                    'error': message,
                }
                return Response(error_response,
                                status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {
                    'message': "One of the required fields is missing or "
                               "request is not formatted correctly",
                    "error": str(e), "status": status.HTTP_400_BAD_REQUEST},
                status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            self.queryset.filter(id=pk).delete()
            return Response({'message': "deleted data with id {}".format(
                str(pk)), "status": status.HTTP_200_OK},
                status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": str(e),
                             "status": status.HTTP_400_BAD_REQUEST},
                            status=status.HTTP_400_BAD_REQUEST)
