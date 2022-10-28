import logging

from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response

from services.v1.views.common import YouPayTransactionCRUD
from core.response_messages import YouPayResponse
from core.constants import PAYMENT_GATEWAY_B2CPAYBACK
from integrations.v1.gateway_clients.b2c_payback import B2CPaybackManager
from payments.constants import (
    PAYMENT_STATUS_AUTHORIZED, PAYMENT_METHOD_TOUCHPOINTS,
    PAYMENT_METHOD_TOUCHPOINTS_AND_CARD
)

logger = logging.getLogger(__name__)


class B2CPaybackPointBalance(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        payback = B2CPaybackManager()
        response = payback.get_point_balance(request.data)
        transaction_id = request.data.get('transaction_id')
        self.update_youpay_transaction_data({
            'transaction_id': transaction_id,
            'payment_gateway': PAYMENT_GATEWAY_B2CPAYBACK
        })
        return Response(response, status=status.HTTP_200_OK)


class B2CPaybackAuthenticate(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        payback = B2CPaybackManager()
        response = payback.authenticate_redemption(request.data)
        transaction_id = request.data.get('transaction_id')
        invoice_amount = float(request.data.get('invoice_amount'))
        selected_amount = float(request.data.get('selected_amount'))
        if invoice_amount == selected_amount: #full redemption
            self.update_youpay_transaction_data({
                'transaction_id': transaction_id,
                'payment_gateway': PAYMENT_GATEWAY_B2CPAYBACK,
                'payment_status': PAYMENT_STATUS_AUTHORIZED,
                'payment_method' : PAYMENT_METHOD_TOUCHPOINTS,

            })
        else: # partial redemption
            self.update_youpay_transaction_data({
                'transaction_id': transaction_id,
                'payment_gateway': PAYMENT_GATEWAY_B2CPAYBACK,
                'payment_status' : PAYMENT_STATUS_AUTHORIZED,
                'payment_method' : PAYMENT_METHOD_TOUCHPOINTS_AND_CARD,
                'payment_scheme' : request.data.get('card_type')
            })
        return Response(response, status=status.HTTP_200_OK)


class B2CPaybackRedemption(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        payback = B2CPaybackManager()
        response = payback.point_redemption()
        # TODO
        #  - create payment request data
        #  -update transaction table with status, payment method, etc
        #  - handle payment response
        return Response(response, status=status.HTTP_200_OK)
