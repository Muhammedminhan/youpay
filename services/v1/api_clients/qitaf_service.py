import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.response_messages import YouPayResponse
from integrations.v1.gateway_clients.qitaf_service import QitafServiceManager

logger = logging.getLogger(__name__)


class QitafGenerateOTPAPIView(APIView):
    response_obj = YouPayResponse()

    def post(self, request):
        """
        request for handling qitaf generate otp api
        """
        try:
            otp_generate_data = {'request_data': request.data}
            qitaf_service = QitafServiceManager()
            response_data, code = qitaf_service.generate_otp(
                otp_generate_data)
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


class QitafCollectPointsAPIView(APIView):
    response_obj = YouPayResponse()

    def post(self, request):
        """
        request for handling qitaf collect points api
        """
        try:
            collect_points_data = {'request_data': request.data}
            qitaf_service = QitafServiceManager()
            response_data, code = qitaf_service.collect_points(
                collect_points_data)
            if response_data:
                data = self.response_obj.get_success_dict(
                    code=code,
                    success_dict=response_data
                )
                return Response(data,
                                status=status.HTTP_200_OK)
            else:
                data = self.response_obj.get_error_dict(error_code=code)
                return Response(data,
                                status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)


class QitafRedeemPointsAPIView(APIView):
    response_obj = YouPayResponse()

    def post(self, request):
        """
        request for handling qitaf points redemption api
        """
        try:
            points_redemption_data = {'request_data': request.data}
            qitaf_service = QitafServiceManager()
            response_data, code = qitaf_service.redeem_points(
                points_redemption_data)
            if response_data:
                data = self.response_obj.get_success_dict(
                    code=code,
                    success_dict=response_data
                )
                return Response(data,
                                status=status.HTTP_200_OK)
            else:
                data = self.response_obj.get_error_dict(error_code=code)
                return Response(data,
                                status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)


class QitafReversePointsAPIView(APIView):
    response_obj = YouPayResponse()

    def post(self, request):
        """
        request for handling qitaf points reversal api
        """
        try:
            points_reversal_data = {'request_data': request.data}
            qitaf_service = QitafServiceManager()
            response_data, code = qitaf_service.reverse_points(
                points_reversal_data)
            if response_data:
                data = self.response_obj.get_success_dict(
                    code=code,
                    success_dict=response_data
                )
                return Response(data,
                                status=status.HTTP_200_OK)
            else:
                data = self.response_obj.get_error_dict(error_code=code)
                return Response(data,
                                status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)


class QitafRewardUpdateAPIView(APIView):
    response_obj = YouPayResponse()

    def post(self, request):
        """
        request for handling qitaf reward update api
        """
        try:
            reward_update_data = {'request_data': request.data}
            qitaf_service = QitafServiceManager()
            response_data, code = qitaf_service.reward_update(
                reward_update_data)
            if response_data:
                data = self.response_obj.get_success_dict(
                    code=code,
                    success_dict=response_data
                )
                return Response(data,
                                status=status.HTTP_200_OK)
            else:
                data = self.response_obj.get_error_dict(error_code=code)
                return Response(data,
                                status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)
