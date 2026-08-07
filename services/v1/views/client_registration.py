import logging

from django.conf import settings
from django.db import transaction, IntegrityError
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from rest_framework.authentication import BasicAuthentication
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework.views import APIView

from core.messages import ERROR_MESSAGE, ERROR_MISSING_FIELDS
from core.models import Country, PaymentConfiguration, PaymentMethodConfig
from services.models import APIClient
from services.v1.auth.client_registration_permission import (
    APIClientRegistrationPermission)
from services.v1.constants import CLIENT_WEBHOOK_ENDPOINT_PREFIX
from services.v1.serializers.client_registrattion import (
    APIClientRegistrationSerializer, APIClientRequestSerializer,
    APIClientResponseSerializer)

logger = logging.getLogger(__name__)


class APIClientRegistrationViewSet(ViewSet):
    """
    API endpoint that allows clients to view, create, update and delete
    and store response
    """
    permission_classes = [APIClientRegistrationPermission]
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


class APIClientRegistrationView(APIView):
    """
    Handles registration of new API clients via an authenticated HTTP POST
    request.
    """
    authentication_classes = [BasicAuthentication]
    permission_classes = [APIClientRegistrationPermission, IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """
        Registers a new API client or retrieves an existing one.

        Validates the request data, creates or retrieves the api client and
        related payment configurations if needed, and returns the client
        details or an error response.
        """
        serializer = APIClientRequestSerializer(
            data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(
                {
                    "errors": {
                        "code": 400,
                        "message": serializer.errors
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        admin = self.get_created_by()
        if not admin:
            return Response(
                {
                    "errors": {
                        "code": 404,
                        "message": "Client registration failed, admin user "
                                   "not found"
                    }
                },
                status=status.HTTP_404_NOT_FOUND
            )
        data = serializer.validated_data

        name = data.get('name', None)
        client_domain = data.get('client_domain', None)
        webhook_url = client_domain + CLIENT_WEBHOOK_ENDPOINT_PREFIX
        is_active = data.get('is_active', True)
        brand_details_path = data.get('brand_details_path', None)
        allow_aed_converted_amount = data.get(
            'show_aed_equivalent_amount', False)
        checkout_channel_code = data.get(
            'currency_channel_config', {})
        logo_file = data.get('logo_file', None)
        mobile_logo_file = data.get('mobile_logo_file', None)
        client_code = data.get('product_code', None)
        allowed_country_codes = data.get(
            'allowed_payment_countries', [])
        payment_method_codes = data.get('payment_method', [])

        with transaction.atomic():
            try:
                client, _ = APIClient.objects.get_or_create(
                    name=name,
                    client_domain=client_domain,
                    client_code=client_code,
                    defaults={
                        'webhook_url': webhook_url,
                        'is_active': is_active,
                        'brand_details_path': brand_details_path,
                        'allow_aed_converted_amount':
                            allow_aed_converted_amount,
                        'logo_file': logo_file,
                        'mobile_logo_file': mobile_logo_file,
                        'checkout_channel_code': checkout_channel_code,
                        'created_by': admin,
                        'modified_by': admin
                    }
                )
            except APIClient.MultipleObjectsReturned:
                logger.error(f"client with name {name}, client code "
                             f"{client_code} and domain {client_domain} "
                             f"found more than once, returning the latest.")

                client = APIClient.objects.filter(
                    name=name, client_domain=client_domain,
                    client_code=client_code
                ).order_by('-id').first()

            for country_code in allowed_country_codes:
                country = Country.objects.get(iso_code=country_code)
                for method_code in payment_method_codes:
                    payment_config = (PaymentConfiguration.objects.get(
                        payment_method=method_code))
                    try:
                        PaymentMethodConfig.objects.create(
                            payment_method=payment_config, country=country,
                            client=client, active=True
                        )
                    except (IntegrityError, ValidationError):
                        logger.error(f"A payment configuration with the same "
                                     f"client-{client.name}, country-"
                                     f"{country.iso_code}, and payment "
                                     f"method-{method_code} already exists")
                        continue


        result = APIClientResponseSerializer(instance=client)
        return Response(result.data, status=status.HTTP_200_OK)

    @staticmethod
    def get_created_by():
        try:
            admin_user_name = settings.ADMIN_USER_NAME
            admin = User.objects.get(username=admin_user_name)
        except User.DoesNotExist:
            logger.error("Admin user not found")
            admin = None
        return admin
