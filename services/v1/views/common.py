from rest_framework import status

from core.constants import PAYMENT_STATUS_CREATED
from payments.serializers.serializers import YGPayTransactionDataSerializer


class YGPayTransactionCRUD(object):
    """
    YGPay Transaction Data CRUD Operations will be here
    """

    def store_ygpay_transaction_data(self, request):
        data = {
            "transaction_id": request.data.get("transaction_id"),
            "amount": request.data.get("amount"),
            "currency": request.data.get("currency"),
            "ip": request.data["payment"].get("ip"),
            "invoice_id": request.data.get("invoice_id"),
            "order_reference": request.data.get("order_reference"),
            "payment_reference": request.data.get("payment_reference"),
            "api_client": request.data.get("api_client"),
            "service_fee": request.data['order'].get("service_fee"),
            "base_amount": request.data['order'].get("base_amount"),
            "VAT_amount": request.data['order'].get("VAT"),
            "order_history": request.data.get("order_history"),
            "payment_gateway": request.data.get("payment_gateway"),
            "payment_status": PAYMENT_STATUS_CREATED,
        }

        serializer = YGPayTransactionDataSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return {"status": status.HTTP_201_CREATED,
                    "data": serializer.data, "message": "created"}
        else:
            return {"status": status.HTTP_400_BAD_REQUEST,
                    "data": serializer.errors, "message": "not created"}
