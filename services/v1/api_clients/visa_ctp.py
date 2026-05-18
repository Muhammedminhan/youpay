import logging

from core.response_messages import YouPayResponse
from core.utils import decrypt_string
from integrations.v1.gateway_clients.visa_ctp import VisaManager
from services.v1.views.common import YouPayTransactionCRUD
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)


class VisaCTPCreateSession(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        """
        API for providing Visa Click to Pay Capture Context to Frontend
        """
        try:
            transaction_id = request.data.get('transaction_id')
            decrypted_id = decrypt_string(transaction_id)
            transaction_obj = self.get_youpay_transaction_data(decrypted_id)

            if transaction_obj:
                visa_manager = VisaManager()
                response_data, status_code = (
                    visa_manager.create_visa_session(transaction_obj))

                if status_code == visa_manager.SUCCESS and response_data:
                    data = self.response_obj.get_success_dict(
                        code=YouPayResponse.SUCCESS,
                        success_dict={'data': response_data}
                    )
                    return Response(data, status=status.HTTP_200_OK)
                else:
                    error_data = self.response_obj.get_error_dict(
                        error_code=status_code)
                    return Response(error_data.get('errors'),
                        status=status.HTTP_400_BAD_REQUEST)

            else:
                data = self.response_obj.get_404_message(
                    message="Transaction does not exist"
                )
                return Response(data, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            logger.error(f"VisaCTPCreateSession Error: {str(e)}")
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'), status=status.HTTP_400_BAD_REQUEST)


class VisaCTPPayment(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        """
        API to process the actual payment after Visa Click to Pay interaction
        """
        try:
            transaction_id = request.data.get('transaction_id')
            visa_transient_token = request.data.get('visa_transient_token')

            transaction_obj = self.get_youpay_transaction_data(
                decrypt_string(transaction_id)
            )

            if transaction_obj:
                visa_manager = VisaManager()
                response_data, status_code = visa_manager.process_visa_payment(
                    transaction_obj, visa_transient_token
                )

                if status_code == self.response_obj.SUCCESS:
                    data = self.response_obj.get_success_dict(
                        code=self.response_obj.SUCCESS,
                        success_dict={'data': response_data}
                    )
                    return Response(data, status=status.HTTP_200_OK)

                # Handle 3DS Pre-Auth Redirect
                if status_code == self.response_obj.PRE_AUTH:
                    return Response(response_data, status=status.HTTP_200_OK)

                # Standard Error Response
                error_data = self.response_obj.get_error_dict(
                    error_code=status_code)
                return Response(error_data.get('errors'),
                                status=status.HTTP_400_BAD_REQUEST)

            return Response({"error": "Transaction not found"},
                            status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            logger.error(f"Error in VisaCTPPayment: {str(e)}")
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)
