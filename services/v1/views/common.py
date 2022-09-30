import logging

from rest_framework import status

from core.messages import ERROR_MISSING_FIELDS
from payments.models import YouPayTransactionData
from payments.serializers.youpay_payments import (
    YouPayTransactionDataSerializer
)
from services.models import APIClient

logger = logging.getLogger(__name__)


class YouPayTransactionCRUD(object):
    """
    YouPay Transaction Data CRUD Operations will be here
    """

    def create_youpay_transaction_data(self, request):
        serializer = YouPayTransactionDataSerializer(data=request)
        if serializer.is_valid():
            serializer.save()
            return {"status": status.HTTP_201_CREATED,
                    "data": serializer.data, "message": "created"}
        else:
            errors = serializer.errors.keys()
            missing_fields = ', '.join(
                ["".join(missing) for missing in errors])
            message = "{}{}".format(ERROR_MISSING_FIELDS, missing_fields)
            return {"status": status.HTTP_400_BAD_REQUEST,
                    "data": serializer.errors, "message": message}

    def get_youpay_transaction_data(self, transaction_id):
        try:
            transaction_obj = YouPayTransactionData.objects.get(
                transaction_id=transaction_id)
            return transaction_obj
        except YouPayTransactionData.DoesNotExist:
            logger.error("Unable to find youpay transaction object for {}"
                         "".format(transaction_id))
            return None

    def update_youpay_transaction_data(self, data):
        """Method to update youpay transaction data"""
        transaction_id = data.get('transaction_id')
        try:
            YouPayTransactionData.objects.filter(
                transaction_id=transaction_id).update(**data)
            logger.info(
                "YouPay transaction data updated successfully for transaction"
                "id{}".format(transaction_id))
        except YouPayTransactionData.DoesNotExist:
            logger.error("Unable to find youpay transaction object for {}"
                         "".format(transaction_id))


class ClientValidator(object):
    """
    Client Validation will be here
    """

    def validate_client(self, request):
        client_id = ''
        api_key = request.META.get('HTTP_X_API_KEY', None)
        if api_key:
            try:
                client = APIClient.objects.get(api_key=api_key)
                if client:
                    client_id = client.pk
                    return True, client_id
                return False, client_id
            except Exception as e:
                logger.info("Exception occurred when validating the client {}"
                            .format(str(e)))
                return False, client_id
        return False, client_id


class PaymentRequestDataValidator(object):
    """
    Payment Request Data Validation will be here
    """

    def validate_payment_request_data(self, request):
        if request.data.get("payment"):
            if request.data["payment"].get("ip"):
                return True
            return False
        return False
