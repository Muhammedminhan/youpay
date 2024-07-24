import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.response_messages import YouPayResponse
from core.utils import decrypt_string
from integrations.common import update_brand_details
from integrations.v1.gateway_clients.mokafa_service import MokafaServiceManager
from payments.constants import PAYMENT_METHOD_MOKAFA
from services.v1.views.common import YouPayTransactionCRUD

logger = logging.getLogger(__name__)


class UpdateMokafaPhoneNumber(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        try:
            transaction_id = request.data.get('transaction_id')
            mokafa_phone_number = request.data.get('mokafa_phone_number')
            mokafa_cic_number = request.data.get('mokafa_cic_number')

            transaction_obj = self.get_youpay_transaction_data(
                decrypt_string(transaction_id))
            if transaction_obj:
                is_updated, brand_details = update_brand_details(
                    transaction_obj)
                if not is_updated:
                    data = self.response_obj.get_error_dict(
                        error_code=(
                            self.response_obj.MOKAFA_PHONE_NUMBER_SAVE_FAILED))
                    return Response(data,
                                    status=status.HTTP_400_BAD_REQUEST)

                update_data = {
                    'transaction_id': transaction_obj.transaction_id,
                    'points_collected_mobile_number': mokafa_phone_number,
                    'points_collected_cic_number': mokafa_cic_number,
                    'point_program': PAYMENT_METHOD_MOKAFA,
                    'point_collection_enabled': True,
                    "brand_details": brand_details
                }
                mokafa_obj = MokafaServiceManager()
                result = mokafa_obj.update_points_collected_mobile_number(
                    update_data)
                if result:
                    data = self.response_obj.get_success_dict(
                        code=self.response_obj.MOKAFA_PHONE_NUMBER_SAVED,
                        success_dict={}
                    )
                    return Response(data, status=status.HTTP_200_OK)
                else:
                    logger.error("Couldn't Update Mokafa phone/cic number for"
                                 " {}".format(transaction_obj.transaction_id))
                    data = self.response_obj.get_error_dict(
                        error_code=(
                            self.response_obj.MOKAFA_PHONE_NUMBER_SAVE_FAILED))
                    return Response(data,
                                    status=status.HTTP_400_BAD_REQUEST)

            else:
                data = self.response_obj.get_error_dict(
                    error_code=self.response_obj.TRANSACTION_NOT_FOUND)
                return Response(data, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)
