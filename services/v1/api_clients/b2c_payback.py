import json
import logging
from decimal import Decimal

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.constants import PAYMENT_GATEWAY_B2CPAYBACK
from core.response_messages import YouPayResponse
from integrations.v1.gateway_clients.b2c_payback import B2CPaybackManager
from payments.constants import (
    PAYMENT_STATUS_AUTHORIZED, PAYMENT_METHOD_TOUCHPOINTS,
    PAYMENT_METHOD_TOUCHPOINTS_AND_CARD, PAYMENT_METHOD_ADCB_CARD_ONLY,
    PAYMENT_STATUS_PAID, PAYMENT_STATUS_PENDING
)
from services.v1.constants import B2C_PAYBACK_NO_RESPONSE_MESSAGE
from services.v1.views.common import (
    YouPayTransactionCRUD, cancelled_payment_check)

logger = logging.getLogger(__name__)


class B2CPaybackPointBalance(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        payback = B2CPaybackManager()
        response, transaction_id = payback.get_point_balance(request.data)
        request_data = request.data
        response_data = response.json()
        if response and response.status_code == 200:
            self.update_youpay_transaction_data({
                'transaction_id': transaction_id,
                'payment_gateway': PAYMENT_GATEWAY_B2CPAYBACK,
                'payment_status': PAYMENT_STATUS_PENDING,
                'card_bin': request_data.get('card_no', "")[0:6],
                'card_last4': request_data.get('card_no', "")[-4:],
                'name_on_card': request_data.get('name_on_card', ""),
                'available_amount': response_data.get('available_amount'),
                'available_points': response_data.get('available_points')
            })
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            try:
                response_text = json.loads(response.text)
                resp_code = response_text.get('code', False)
                message = response_text.get('message', None)
                response = {'errors': {
                    'code': resp_code, 'message': message}}
            except Exception as e:
                logger.error("Failed response received from b2cpayback "
                             "point balance endpoint", exc_info=e)
                response = {'errors': {
                    'code': "400", 'message': B2C_PAYBACK_NO_RESPONSE_MESSAGE}
                }
            return Response(response, status=status.HTTP_400_BAD_REQUEST)


@cancelled_payment_check
class B2CPaybackAuthenticate(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        payback = B2CPaybackManager()
        response, transaction_obj = payback.authenticate_redemption(
            request.data)
        if response:
            invoice_amount = transaction_obj.amount
            selected_amount = Decimal(request.data.get('selected_amount'))
            checkout_amount = Decimal(request.data.get('checkout_amount'))
            update_data = {
                'transaction_id': transaction_obj.transaction_id,
                'payment_gateway': PAYMENT_GATEWAY_B2CPAYBACK,
                'payment_status': PAYMENT_STATUS_AUTHORIZED,
                'is_gcc_card': True,
                'payable_amount': checkout_amount,
                'available_amount': transaction_obj.available_amount,
                'available_points': transaction_obj.available_points,
                'is_full_redemption': response.get('is_full_redemption')
            }

            if invoice_amount == selected_amount:  # full redemption
                update_data['payment_method'] = PAYMENT_METHOD_TOUCHPOINTS

            elif selected_amount > 0 and checkout_amount > 0:  # partial redemption
                update_data['payment_method'] = (
                    PAYMENT_METHOD_TOUCHPOINTS_AND_CARD)
                update_data['payment_scheme'] = request.data.get('card_type')

            else:  # full amount from card
                update_data['payment_method'] = PAYMENT_METHOD_ADCB_CARD_ONLY
                update_data['payment_scheme'] = request.data.get('card_type')

            self.update_youpay_transaction_data(update_data)
            return Response(response, status=status.HTTP_200_OK)
        else:
            try:
                response_text = json.loads(response.text)
                resp_code = response_text.get('code', False)
                message = response_text.get('message', None)
                response = {'errors': {
                    'code': resp_code, 'message': message}}
            except Exception as e:
                logger.error("Failed response received from b2cpayback "
                             "authenticate endpoint", exc_info=e)
                response = {'errors': {
                    'code': "400", 'message':
                        B2C_PAYBACK_NO_RESPONSE_MESSAGE}}
            return Response(response, status=status.HTTP_400_BAD_REQUEST)


@cancelled_payment_check
class B2CPaybackRedemption(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        payback = B2CPaybackManager()
        response, transaction_obj = payback.point_redemption(request.data)
        transaction_id = (transaction_obj.transaction_id if transaction_obj
                          else None)
        if response:
            if response.get('results', {}).get('redemption_status') == True:
                update_data = {
                    'transaction_id': transaction_obj.transaction_id,
                    'payment_status': PAYMENT_STATUS_PAID,
                    'payment_reference': response.get(
                        'results', {}).get('reference_id'),
                    'approved': True,
                    "redeemed_amount": response.get(
                        'results', {}).get('redeemed_amount'),
                    "redeemed_points": response.get(
                        'results', {}).get('redeemed_points'),
                    'available_amount': response.get(
                        'results', {}).get('available_amount'),
                    'available_points': transaction_obj.available_points,
                    'payable_amount': transaction_obj.payable_amount,
                    'is_full_redemption': transaction_obj.is_full_redemption
                }
                self.update_youpay_transaction_data(update_data)
            else:
                logger.info(
                    "Point redemption not successful for transaction id "
                    "{}".format(transaction_id))
            return Response(response, status=status.HTTP_200_OK)
        else:
            try:
                response_text = json.loads(response.text)
                resp_code = response_text.get('code', False)
                message = response_text.get('message', None)
                response = {'errors': {
                    'code': resp_code, 'message': message}}
            except Exception as e:
                logger.error("Failed response received from b2cpayback "
                             "redemption endpoint", exc_info=e)
                response = {'errors': {
                    'code': "400", 'message': B2C_PAYBACK_NO_RESPONSE_MESSAGE}
                }
            return Response(response, status=status.HTTP_400_BAD_REQUEST)


class B2CPaybackVerify(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def get(self, request, *args, **kwargs):
        payback = B2CPaybackManager()
        payment_data = {
            'transaction_id': request.query_params.get('id'),
            'redemption_reference_id': request.query_params.get(
                'redemption_reference_id'),
            'cko-session-id': request.query_params.get(
                'cko-session-id')}
        response, transaction_obj = payback.verification(payment_data)
        transaction_id = (transaction_obj.transaction_id if transaction_obj
                          else None)
        if response:
            if response.get('results', {}).get('payment_status') == True:
                update_data = {
                    'transaction_id': transaction_obj.transaction_id,
                    'payment_status': PAYMENT_STATUS_PAID,
                    'payment_reference': (response.get('payment_reference')
                                          if response.get('payment_reference')
                                          else response.get(
                        'results', {}).get('reference_id')),
                    'is_flagged': response.get('is_flagged', False),
                    'approved': True,
                    'redeemed_amount': response.get(
                        'results', {}).get('redeemed_amount'),
                    'redeemed_points': response.get(
                        'results', {}).get('redeemed_points'),
                    'is_gcc_card': True,
                    'available_amount': response.get(
                        'results', {}).get('available_amount'),
                    'available_points': transaction_obj.available_points,
                    'payable_amount': transaction_obj.payable_amount,
                    'is_full_redemption': transaction_obj.is_full_redemption
                }
                self.update_youpay_transaction_data(update_data)
            else:
                logger.info("Verification unsuccessful for transaction"
                            " id {}".format(transaction_id))
            return Response(response, status=status.HTTP_200_OK)
        else:
            try:
                response_text = json.loads(response.text)
                resp_code = response_text.get('code', False)
                message = response_text.get('message', None)
                response = {'errors': {
                    'code': resp_code, 'message': message}}
            except Exception as e:
                logger.error("Failed response received from b2cpayback "
                             "verify endpoint", exc_info=e)
                response = {'errors': {
                    'code': "400", 'message': B2C_PAYBACK_NO_RESPONSE_MESSAGE}
                }
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
