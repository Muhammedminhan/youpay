import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.response_messages import YouPayResponse
from core.utils import get_site_domain, decrypt_string
from integrations.common import update_brand_details
from integrations.v1.gateway_clients.citi_service import CitiRewardsManager
from payments.serializers.youpay_payments import (
    YouPayTransactionDataSerializer)
from services.v1.views.common import YouPayTransactionCRUD, ClientValidator

logger = logging.getLogger(__name__)


class CitiGenerateOTPAPIView(YouPayTransactionCRUD, APIView, ClientValidator):
    response_obj = YouPayResponse()

    def post(self, request):
        """
        request for handling citi rewards point balance api
        """
        try:

            site_domain = get_site_domain(request)
            transaction_id = request.data.get('transaction_id')

            transaction_obj = self.get_youpay_transaction_data(
                decrypt_string(transaction_id))
            if transaction_obj:
                brand_details = update_brand_details(
                    transaction_obj)
                if brand_details:
                    serializer = YouPayTransactionDataSerializer(
                        transaction_obj)
                    transaction_data = serializer.data
                    generate_otp_data = {
                        'transaction_data': transaction_data,
                        'request_data': request.data,
                        'site_domain': site_domain
                    }
                    citi_rewards = CitiRewardsManager()

                    response_data, code = citi_rewards.generate_otp(
                        generate_otp_data)

                    if response_data:
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
                    data = self.response_obj.get_404_message(
                        message="Brand details not found")
                    return Response(data, status=status.HTTP_404_NOT_FOUND)
            else:
                data = self.response_obj.get_404_message(
                    message="Transaction doesn't exists")
                return Response(data, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            error = ("Error in citi rewards generate otp service api:"
                     " {}".format(e))
            logger.error(error)
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)


class CitiPointBalanceAPIView(APIView):
    response_obj = YouPayResponse()

    def post(self, request):
        """
        request for handling citi rewards point balance api
        """
        try:
            point_balance_data = {
                'transaction_id': decrypt_string(
                    request.data.get('transaction_id')),
                'reference_id': request.data.get('reference_id'),
                'pin_number': request.data.get('pin_number')
            }

            citi_rewards = CitiRewardsManager()
            response_data, code = citi_rewards.get_point_balance(
                point_balance_data)

            if response_data:
                data = self.response_obj.get_success_dict(
                    code=code,
                    success_dict=response_data
                )
                return Response(data, status=status.HTTP_200_OK)
            else:
                data = self.response_obj.get_error_dict(error_code=code)
                return Response(data, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            error = ("Error in citi rewards point balance service api:"
                     " {}".format(e))
            logger.error(error)
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)


class CitiPointRedemptionAPIView(APIView):
    response_obj = YouPayResponse()

    def get(self, request):
        """
        request for handling citi rewards point redemption api
        """
        try:
            request_data = request.query_params
            transaction_id = decrypt_string(
                request_data.get('id'))
            point_redemption_data = {
                'transaction_id': transaction_id,
                'reference_id': request_data.get('reference_id')
            }
            citi_rewards = CitiRewardsManager()
            response_data, code = citi_rewards.point_redemption(
                point_redemption_data)
            if response_data:
                data = self.response_obj.get_success_dict(
                    code=code,
                    success_dict=response_data
                )
                return Response(data, status=status.HTTP_200_OK)
            else:
                data = self.response_obj.get_error_dict(error_code=code)
                return Response(data, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            error = ("Error in citi rewards point redemption api:"
                     " {}".format(e))
            logger.error(error)
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)
