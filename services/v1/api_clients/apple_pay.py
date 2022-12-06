
from rest_framework.views import APIView
from services.v1.views.common import YouPayTransactionCRUD
from core.response_messages import YouPayResponse
from core.utils import get_site_domain, decrypt_string
from payments.serializers.youpay_payments import (
    YouPayTransactionDataSerializer
)
from services.constants import TOKEN_TYPE_APPLEPAY
from integrations.v1.gateway_clients.checkoutpg import CheckoutpgManager


class ApplePayPayment(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        site_domain = get_site_domain(request)
        transaction_id = request.data.get('transaction_id')

        transaction_obj = self.get_youpay_transaction_data(
            decrypt_string(transaction_id))
        if transaction_obj:
            serializer = YouPayTransactionDataSerializer(transaction_obj)
            transaction_data = serializer.data
            payment_data = {'token_type': TOKEN_TYPE_APPLEPAY,
                            'transaction_data': transaction_data,
                            'request_data': request.data,
                            'site_domain': site_domain}
            checkout = CheckoutpgManager()

        pass
