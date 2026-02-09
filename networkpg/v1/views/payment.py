import logging
import json

from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from core.utils import decrypt_string

from payments.serializers.youpay_payments import (
    YouPayTransactionDataSerializer)

from networkpg.choices import PaymentStatus
from networkpg.libs.client import NetworkPGClient
from networkpg.models import NetworkTransaction
from services.v1.views.payment_handlers import PaymentHandlers

from core.response_messages import YouPayResponse

from networkpg.v1.serializers.payment import (
    PaymentInitiationSerializer, NetworkTransactionSerializer)
from core.constants import (
    REQUEST_METHOD_POST, REQUEST_METHOD_GET
)   
from integrations.constants import (
    PAYMENT_REQUEST_TYPE_PAYMENT, PAYMENT_REQUEST_VERIFY
)

logger = logging.getLogger(__name__)


class NetworkPaymentsApi(APIView, PaymentHandlers):
    """
    View to initiate a payment with Network International.
    """
    client = NetworkPGClient()
    response_obj = YouPayResponse()

    def post(self, request, *_args, **_kwargs):
        transaction_id = request.data.get("transaction_id")
        decrypted_id = decrypt_string(transaction_id)
        logger.info(f"Received Network charge calculation request for "
                    f"Transaction ID: {decrypted_id}")

        transaction_obj = self.get_youpay_transaction_data(decrypted_id)
        if transaction_obj:
            serializer = YouPayTransactionDataSerializer(transaction_obj)
            data = serializer.data

        try:
            payment_serializer = PaymentInitiationSerializer(data=data)
            payment_serializer.is_valid(raise_exception=True)
            network_tx = NetworkTransaction.objects.create(
                **payment_serializer.validated_data,
                youpay_transaction=transaction_obj,
                status=PaymentStatus.PENDING,
            )
            payment_data = {
                "amount": int(float(data["amount"]) * 100),
                "currency": data["currency"],
                "email": data["customer_email"],
                "customer_name": data["customer_name"],
                "payment_reference": data["order_reference"],
                "redirect_url": data.get("redirect_url"),
            }
            with transaction.atomic():
                response = self.client.create_order(payment_data)
                self.create_youpay_to_payment_gateways_data(
                    transaction_obj=transaction_obj,
                    transaction_id=transaction_id,
                    request_data=json.dumps(payment_data),
                    response_data=json.dumps(response),
                    request_method=REQUEST_METHOD_POST,
                    request_type=PAYMENT_REQUEST_TYPE_PAYMENT,
                )
                if response and "_links" in response:
                    payment_url = response["_links"]["payment"]["href"]
                    order_id = response["reference"]

                    # Update local record with response data
                    network_tx.network_order_id = order_id
                    network_tx.network_order_reference = response.get(
                        "referrer"
                    )
                    network_tx.api_response_data = response
                    network_tx.status = PaymentStatus.STARTED
                    network_tx.save()

                    return Response(
                        {
                            "payment_url": payment_url,
                            "order_id": order_id,
                            "payment_reference": payment_serializer["payment_reference"].value,
                            "status": "STARTED",
                        },
                        status=status.HTTP_201_CREATED,
                    )
                else:
                    logger.error("Failed to initiate Network payment: %s", response)
                    network_tx.status = PaymentStatus.FAILED
                    network_tx.api_response_data = response or {"error": "No response"}
                    network_tx.save()
                    return Response(
                        {"error": "Failed to initiate payment with gateway"},
                        status=status.HTTP_502_BAD_GATEWAY,
                    )

        except Exception as e:
            logger.exception("Internal error during payment initiation %s", e)
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def get(self, request, *_args, **_kwargs):
        order_id = request.query_params.get("order_id")
        if not order_id:
            return Response(
                {"error": "order_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        network_tx = NetworkTransaction.objects.get(network_order_id=order_id)
        response = self.client.get_order_status(order_id)
        self.create_youpay_to_payment_gateways_data(
            transaction_obj=network_tx.youpay_transaction,
            transaction_id=network_tx.youpay_transaction.transaction_id,
            request_data=json.dumps(order_id),
            response_data=json.dumps(response),
            request_method=REQUEST_METHOD_GET,
            request_type=PAYMENT_REQUEST_VERIFY,
        )
        if response:
            return self.process_payment_response(response, network_tx)

        data = self.response_obj.get_404_message(
                    message="Failed to fetch order details from gateway")
        return Response(data, status=status.HTTP_404_NOT_FOUND)

    def process_payment_response(self, response, network_tx):
        """
        Process the payment response from Network International.
        """
        order_reference = response.get('reference')
        try:
            serializer = NetworkTransactionSerializer(network_tx)
            response = serializer.save_ni_response(response)
            code = response.get('code')
            return Response(
                self.response_obj.get_success_dict(
                    code=code, success_dict=response),
                status=status.HTTP_200_OK
            )
        except NetworkTransaction.DoesNotExist:
            logger.error(
                f"NetworkTransaction not found for order_id: {order_reference}")
