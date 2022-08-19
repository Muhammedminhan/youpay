import json

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

    def get_queryset(self):
        return super().get_queryset()

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
                {'message': "One of the required fields is missing "
                            "or request is not formatted correctly",
                 "error": str(e),
                 "status": status.HTTP_400_BAD_REQUEST},
                status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        try:
            obj_id = self.request.GET.get('obj_id', "[]")
            if id == "all":
                self.queryset.delete()
                return Response({'message': "deleted all data"},
                                status=status.HTTP_200_OK)
            else:
                obj_id = json.loads(obj_id)
                self.queryset.filter(id__in=obj_id).delete()
                return Response({'message': "deleted data with id {}".format(
                    str(obj_id))}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": str(e),
                             "status": status.HTTP_400_BAD_REQUEST},
                            status=status.HTTP_400_BAD_REQUEST)
