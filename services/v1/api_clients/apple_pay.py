import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.messages import TRANSACTION_DOESNT_EXIST
from core.response_messages import YouPayResponse
from core.utils import decrypt_string
from integrations.v1.gateway_clients.apple_pay import ApplePayManager
from payments.serializers.youpay_payments import (
    ApplepayPaymentDataSerializer,
    YouPayTransactionDataSerializer
)
from services.v1.views.common import YouPayTransactionCRUD, ClientValidator

logger = logging.getLogger(__name__)


class ApplePayStatusUpdateAPI(YouPayTransactionCRUD, APIView,
                              ClientValidator):
    response_obj = YouPayResponse()

    def post(self, request):
        '''
        Applepay authorize API
        '''
        print("ApplePayStatusUpdateAPI ", request.data)
        try:
            transaction_id = request.data.get('transaction_id')
            transaction_obj = self.get_youpay_transaction_data(
                decrypt_string(transaction_id))
            if transaction_obj:
                serializer = ApplepayPaymentDataSerializer(transaction_obj)
                transaction_data = serializer.data

                payment_data = {
                    'transaction_data': transaction_data,
                    'transaction_obj': transaction_obj,
                    'payment_stage': request.data.get('payment_stage'),
                    'status': request.data.get('status'),

                    # TODO : Future case, to keep track of the flow
                    'request_data': request.data.get('request_data'),
                    'response_data': request.data.get('response_data')
                }
                apple_pay = ApplePayManager()
                response_data, code = apple_pay.update_status(
                    payment_data)
                if code == YouPayResponse.APPLE_PAY_SUCCESS:
                    data = self.response_obj.get_success_dict(
                        code=code,
                        success_dict=response_data
                    )
                    return Response(data,
                                    status=status.HTTP_200_OK)
                else:
                    data = self.response_obj.get_success_dict(
                        code=code,
                        success_dict=response_data
                    )
                    return Response(data,
                                    status=status.HTTP_400_BAD_REQUEST)

            else:
                data = self.response_obj.get_404_message(
                    message=TRANSACTION_DOESNT_EXIST)
                return Response(data, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)

