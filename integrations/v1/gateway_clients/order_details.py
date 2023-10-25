import logging

import requests
from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from core.response_messages import YouPayResponse
from core.utils import decrypt_string
from integrations.constants import ORDER_DETAILS_API, ECOM_API_CLIENT_CODE
from payments.models import YouPayTransactionData
from services.v1.views.utils import get_client_for_configuration

logger = logging.getLogger(__name__)


class OrderDetailsManage(ViewSet):
    """
    Order details Manage viewset for getting order details
    """
    response_obj = YouPayResponse()

    def retrieve(self, request, pk=None):
        decrypted_transaction_id = decrypt_string(pk)
        try:
            logger.info("Fetching brand details to youpay transaction table "
                        "for transaction, {}".format(decrypted_transaction_id))

            transaction = YouPayTransactionData.objects.get(
                transaction_id=decrypted_transaction_id)
            if transaction:

                client = get_client_for_configuration(transaction)
                if not client:
                    message = "Client doesn't exists"
                    data = self.response_obj.get_404_message(
                        message=message)

                    return Response(data,
                                    status=status.HTTP_404_NOT_FOUND)
                elif client.client_code != ECOM_API_CLIENT_CODE:
                    message = "Brand details not available for this client"
                    data = self.response_obj.get_404_message(message=message)
                    return Response(data,
                                    status=status.HTTP_404_NOT_FOUND)

                invoice = transaction.invoice_id
                order_details = self.get_order_details(client, invoice)
                transaction.brand_details = order_details
                transaction.save()

                data = self.response_obj.get_success_dict(
                    code=self.response_obj.SUCCESS)
                return Response(data,
                                status=status.HTTP_200_OK)

            else:
                data = self.response_obj.get_error_dict(
                    error_code=self.response_obj.UNKNOWN_ERR)
                return Response(data.get('errors'),
                                status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            data = self.response_obj.get_404_message(message=str(e))
            return Response(
                data,
                status=status.HTTP_404_NOT_FOUND)

    def get_order_details(self, client, invoice):
        """
        to get the order details from the client
        """
        api_key = client.api_key
        api_secret = client.api_secret

        headers = {
            'API-KEY': api_key,
            'API-SECRET': api_secret
        }

        try:
            logger.info("Fetching order details from client started for "
                        "invoice {}".format(invoice))

            url = client.client_domain + ORDER_DETAILS_API + invoice
            response = requests.get(url, headers=headers)

            if response:
                response_data = response.json()
                return response_data
            else:
                logger.error(
                    "Unable to get response on order details for invoice {}"
                    .format(invoice))
                return None

        except Exception as e:
            logger.error("Unable to get order details for invoice {}"
                         .format(invoice))
            return None
