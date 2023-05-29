import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.response_messages import YouPayResponse
from integrations.v1.gateway_clients.citi_service import CitiRewardsManager

logger = logging.getLogger(__name__)


class CitiPointBalanceAPIView(APIView):
    response_obj = YouPayResponse()

    def post(self, request):
        """
        request for handling citi rewards point balance api
        """
        try:
            point_balance_data = {'request_data': request.data}
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
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)


class CitiPointRedemptionAPIView(APIView):
    response_obj = YouPayResponse()

    def post(self, request):
        """
        request for handling citi rewards point redemption api
        """
        try:
            point_redemption_data = {'request_data': request.data}
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
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)
