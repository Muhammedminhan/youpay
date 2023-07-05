import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.response_messages import YouPayResponse
from core.utils import decrypt_string
from integrations.v1.gateway_clients.qitaf_service import QitafServiceManager
from services.v1.views.common import YouPayTransactionCRUD

logger = logging.getLogger(__name__)


class UpdateQitafPhoneNumber(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        try:
            transaction_id = request.data.get('transaction_id')
            qitaf_phone_number = request.data.get('qitaf_phone_number')

            transaction_obj = self.get_youpay_transaction_data(
                decrypt_string(transaction_id))
            if transaction_obj:
                data = {
                    'transaction_id': transaction_obj.transaction_id,
                    'qitaf_phone_number': qitaf_phone_number,
                    'is_qitaf_enabled': str(True)
                }
                qitaf_service = QitafServiceManager()
                result = qitaf_service.update_qitaf_phone_number(data)
                if result:
                    data = self.response_obj.get_success_dict(
                        code=self.response_obj.QITAF_PHONE_NUMBER_SAVED,
                        success_dict={}
                    )
                    return Response(data, status=status.HTTP_200_OK)
                else:
                    logger.error("Couldn't Update Qitaf phone number for {}"
                                 "".format(transaction_obj.transaction_id))
                    data = self.response_obj.get_error_dict(
                        error_code=(
                            self.response_obj.QITAF_PHONE_NUMBER_SAVE_FAILED))
                    return Response(data,
                                    status=status.HTTP_400_BAD_REQUEST)

            else:
                data = self.response_obj.get_404_message(
                    message="Transaction doesn't exists")
                return Response(data, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)


class QitafGenerateOTPAPIView(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        """
        request for handling qitaf generate otp api
        """
        try:
            transaction_id = request.data.get('transaction_id')
            transaction_obj = self.get_youpay_transaction_data(
                decrypt_string(transaction_id))
            if transaction_obj:
                if transaction_obj.qitaf_phone_number is None:
                    data = (self.response_obj.get_error_dict(error_code=(
                        self.response_obj.QITAF_PHONE_NUMBER_FAILED_TO_FETCH))
                    )
                    return Response(data, status=status.HTTP_400_BAD_REQUEST)

                otp_generate_data = {'request_data': {
                    'transaction_obj': transaction_obj,
                    "mobile_number": transaction_obj.qitaf_phone_number

                }}
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
            else:
                data = self.response_obj.get_404_message(
                    message="Transaction doesn't exists")
                return Response(data, status=status.HTTP_404_NOT_FOUND)
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
    # TODO : Convert this is an admin action instead of calling api
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
    # TODO : No api need for this, this will be an automated process while doing the payment
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
