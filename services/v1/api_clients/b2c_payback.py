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
    PAYMENT_METHOD_TOUCHPOINTS_AND_CARD, PAYMENT_METHOD_ADCB_CARD_ONLY,
    PAYMENT_STATUS_PAID
)

logger = logging.getLogger(__name__)


class B2CPaybackPointBalance(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        payback = B2CPaybackManager()
        response, transaction_id = payback.get_point_balance(request.data)
        if response:
            self.update_youpay_transaction_data({
                'transaction_id': transaction_id,
                'payment_gateway': PAYMENT_GATEWAY_B2CPAYBACK
            })
            return Response(response, status=status.HTTP_200_OK)
        else:
            response = {'errors': {
                'code': 400, 'message': "youpay point balance method failed"}}
            return Response(response, status=status.HTTP_400_BAD_REQUEST)


class B2CPaybackAuthenticate(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        payback = B2CPaybackManager()
        response, transaction_id = payback.authenticate_redemption(
            request.data)
        if response:
            invoice_amount = float(request.data.get('invoice_amount'))
            selected_amount = float(request.data.get('selected_amount'))
            update_data = {
                    'transaction_id': transaction_id ,
                    'payment_gateway': PAYMENT_GATEWAY_B2CPAYBACK,
                    'payment_status': PAYMENT_STATUS_AUTHORIZED,
                }
            if invoice_amount == selected_amount: #full redemption
                update_data['payment_method'] = PAYMENT_METHOD_TOUCHPOINTS

            elif selected_amount > 0: # partial redemption
                update_data['payment_method'] = (
                    PAYMENT_METHOD_TOUCHPOINTS_AND_CARD)
                update_data['payment_scheme'] = request.data.get('card_type')

            else: # full amount from card
                update_data['payment_method'] = PAYMENT_METHOD_ADCB_CARD_ONLY
                update_data['payment_scheme'] = request.data.get('card_type')

            self.update_youpay_transaction_data(update_data)
            return Response(response, status=status.HTTP_200_OK)
        else:
            response = {'errors': {
                'code': 400, 'message': "youpay b2cpayback authentication"
                                        " method failed"}}
            return Response(response, status=status.HTTP_400_BAD_REQUEST)


class B2CPaybackRedemption(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        payback = B2CPaybackManager()
        response, transaction_id = payback.point_redemption(request.data)
        if response:
            if response.get('results',"").get('redemption_status',"") == True:
                update_data = {
                    'transaction_id': transaction_id,
                    'payment_status': PAYMENT_STATUS_PAID,
                }
                self.update_youpay_transaction_data(update_data)
            else:
                logger.info("Point redemption not successful for transaction id "
                            "{}".format(transaction_id))
            return Response(response, status=status.HTTP_200_OK)
        else:
            response = {'errors': {
                'code': 400, 'message': "youpay b2cpayback redemption"
                                        " method failed"}}
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
