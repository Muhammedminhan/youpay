import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.response_messages import YouPayResponse
from core.utils import decrypt_string
from integrations.constants import QITAF_CLIENT_CODE
from integrations.v1.gateway_clients.neqaty_service import (
    NeqatyServiceManager)
from services.v1.views.common import YouPayTransactionCRUD

logger = logging.getLogger(__name__)


class NeqatyPointBalanceAPIView(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        """
        request for handling Neqaty generate otp api
        """
        logger.info("NeqatyPointBalanceAPIView request data : {}".format(
            request.data))

        try:
            mobile_number = request.data.get('mobile_number')
            transaction_id = request.data.get('transaction_id')
            transaction_obj = self.get_youpay_transaction_data(
                decrypt_string(transaction_id))
            if transaction_obj:

                payload = {
                    'client_code': QITAF_CLIENT_CODE,
                    'invoice_id': transaction_obj.invoice_id,
                    'platform': transaction_obj.platform,
                    'customer_name': transaction_obj.customer_name,
                    'customer_email': transaction_obj.customer_email,
                    "msisdn": mobile_number,
                    "transaction_obj": transaction_obj
                }
                neqaty_service = NeqatyServiceManager()
                response_data, code = neqaty_service.point_balance(
                    payload)

                if response_data and code == self.response_obj.SUCCESS:
                    data = self.response_obj.get_success_dict(
                        code=code,
                        success_dict=response_data
                    )
                    return Response(data, status=status.HTTP_200_OK)
                else:
                    data = self.response_obj.get_error_dict(
                        error_code=code)
                    return Response(data,
                                    status=status.HTTP_400_BAD_REQUEST)

            else:
                data = self.response_obj.get_error_dict(
                    error_code=self.response_obj.TRANSACTION_NOT_FOUND)
                logger.error(
                    "NeqatyPointBalanceAPIView : Transaction not found for {}"
                    "".format(transaction_id))
                return Response(data, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            logger.error(
                "Exception occurred on NeqatyPointBalanceAPIView : {}".format(
                    str(e)), exc_info=True)
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)
