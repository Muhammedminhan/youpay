import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.messages import TRANSACTION_DOESNT_EXIST
from core.response_messages import YouPayResponse
from core.utils import decrypt_string
from integrations.v1.gateway_clients.apple_pay import ApplePayManager
from payments.serializers.youpay_payments import (
    YouPayTransactionDataSerializer
)
from services.v1.views.common import YouPayTransactionCRUD, ClientValidator

logger = logging.getLogger(__name__)


class ApplePayInitializeAPI(YouPayTransactionCRUD, APIView,
                            ClientValidator):
    response_obj = YouPayResponse()

    def post(self, request):
        '''
        Applepay initialize API
        '''
        try:
            transaction_id = request.data.get('transaction_id')
            transaction_obj = self.get_youpay_transaction_data(
                decrypt_string(transaction_id))
            if transaction_obj:
                serializer = YouPayTransactionDataSerializer(transaction_obj)
                transaction_data = serializer.data
                payment_data = {'transaction_data': transaction_data,
                                'transaction_obj': transaction_obj,
                                'request_data': request.data}
                apple_pay = ApplePayManager()
                response_data, code = apple_pay.initialize_applepay(
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


class ApplePayAuthorizeAPI(YouPayTransactionCRUD, APIView,
                           ClientValidator):
    response_obj = YouPayResponse()

    def post(self, request):
        '''
        Applepay authorize API
        '''
        try:
            transaction_id = request.data.get('transaction_id')
            transaction_obj = self.get_youpay_transaction_data(
                decrypt_string(transaction_id))
            if transaction_obj:
                serializer = YouPayTransactionDataSerializer(transaction_obj)
                transaction_data = serializer.data
                        
                        
                verify_response, verify_status = self.verify_transaction(
                    transaction_data)

                is_verified = verify_response.get('is_verified', False)
                if verify_status == status.HTTP_200_OK and is_verified:
                
                
                    payment_data = {
                        'transaction_data': transaction_data,
                        'transaction_obj': transaction_obj,

                        'request_data': request.data.get('request_data'),
                        'response_data': request.data.get('response_data')}
                    apple_pay = ApplePayManager()
                    response_data, code = apple_pay.authorize_applepay(
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
                    msg = (
                        "Youpay transaction verification failed for "
                        "transaction id {} response is : {} ".format(
                            self.transaction_id, verify_response))
                    logger.error(msg)
                    return (
                        verify_response,
                        self.CLIENT_TRANSACTION_VERIFICATION_FAILED)
            else:
                data = self.response_obj.get_404_message(
                    message=TRANSACTION_DOESNT_EXIST)
                return Response(data, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)


class ApplePayPaymentAPI(YouPayTransactionCRUD, APIView,
                         ClientValidator):
    response_obj = YouPayResponse()

    def post(self, request):
        '''
        Applepay payment API
        request body example:
        {
            "transaction_id": "transaction_id",
            "request_data": {...},
            "response_data": {...}
        }
        
        '''
        try:
            transaction_id = request.data.get('transaction_id')
            transaction_obj = self.get_youpay_transaction_data(
                decrypt_string(transaction_id))
            if transaction_obj:
                serializer = YouPayTransactionDataSerializer(transaction_obj)
                transaction_data = serializer.data
                payment_data = {
                    'transaction_data': transaction_data,
                    'transaction_obj': transaction_obj,
                    'request_data': request.data.get('request_data'),
                    'response_data': request.data.get('response_data'),
                }
                apple_pay = ApplePayManager()
                response_data, code = apple_pay.applepay_payment(
                    payment_data)

                if code == YouPayResponse.APPLE_PAY_SUCCESS:
                    data = self.response_obj.get_success_dict(
                        code=code,
                        success_dict=response_data
                    )
                    return Response(data, status=status.HTTP_200_OK)
                else:
                    data = self.response_obj.get_success_dict(
                        code=code, success_dict=response_data
                    )
                    return Response(data, status=status.HTTP_400_BAD_REQUEST)
            else:
                data = self.response_obj.get_404_message(
                    message=TRANSACTION_DOESNT_EXIST)
                return Response(data, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            data = self.response_obj.get_400_message(message=str(e))

            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)
