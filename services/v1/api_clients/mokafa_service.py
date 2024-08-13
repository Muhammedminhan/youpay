import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.messages import (IS_SUCCESS, COMMON_ERROR_MESSAGE_EN,
                           COMMON_ERROR_MESSAGE_EN_CODE)
from core.response_messages import YouPayResponse
from core.utils import decrypt_string
from integrations.common import update_brand_details
from integrations.v1.gateway_clients.mokafa_service import MokafaServiceManager
from integrations.v1.serializers.mokafaa_serializers import (
    MokafaaRedemptionSerializer)
from payments.constants import PAYMENT_METHOD_MOKAFAA
from services.v1.serializers.payment_request import OTPSerializer
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
                    'point_program': PAYMENT_METHOD_MOKAFAA,
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


class MokafaaGenerateOTPAPIView(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        """
        request for handling mokafaa generate otp api
        """
        logger.info("MokafaaGenerateOTPAPIView request data : {}".format(
            request.data))

        try:
            mobile_number = request.data.get('mobile_number')
            otp_serializer = OTPSerializer(data=request.data)
            if otp_serializer.is_valid(raise_exception=True):
                transaction_obj = otp_serializer.transaction_obj
                payload = {'request_data': {
                    'transaction_obj': transaction_obj,
                    "mobile_number": mobile_number
                }}
                mokafaa_service = MokafaServiceManager()
                response_data, code = mokafaa_service.generate_otp(payload)

                if response_data and code == self.response_obj.SUCCESS:
                    data = self.response_obj.get_success_dict(
                        code=code,
                        success_dict=response_data
                    )
                    return Response(data, status=status.HTTP_200_OK)
                else:
                    data = self.response_obj.get_error_dict(error_code=code)
                    return Response(data, status=status.HTTP_400_BAD_REQUEST)
            else:
                data = self.response_obj.get_error_dict(
                    error_code=self.response_obj.TRANSACTION_NOT_FOUND)
                return Response(data, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(
                "Exception occurred on MokafaaGenerateOTPAPIView : {}".format(
                    str(e)), exc_info=True)
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)


class MokafaaRedeemPointsAPIView(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        """
        request for handling mokafaa points redemption api
        1.full redemption
        2.partial redemption
        """
        try:
            logger.info("MokafaaRedeemPointsAPIView API triggered, request "
                        "data: {}".format(request.data))
            mokafaa_redemption_serializer = MokafaaRedemptionSerializer(
                data=request.data, context={'request': request})

            mokafaa_redemption_serializer.is_valid(raise_exception=True)
            validated_data = mokafaa_redemption_serializer.data

            points_redemption_data = validated_data

            selected_amount_in_req = request.data.get("selected_amount")
            transaction_order_reference = (
                mokafaa_redemption_serializer.transaction_obj.order_reference)
            points_redemption_data.update(
                {
                    "transaction_obj": (
                        mokafaa_redemption_serializer.transaction_obj),
                    "referance_id": (
                        mokafaa_redemption_serializer.transaction_obj.
                        payment_reference),
                    "one_time_password": validated_data.get('pin_number'),
                    "selected_amount": selected_amount_in_req,
                    "checkout_amount": validated_data.get('checkout_amount'),
                    "is_save_user_token": validated_data.get(
                        'is_save_user_token'),
                    "customer_name": validated_data.get('customer_name'),
                    "cvv": validated_data.get('cvv'),
                    "token": validated_data.get('token'),
                    "token_type": validated_data.get('token_type'),
                    "encrypted_id": request.data.get('transaction_id'),
                    "brand_calculations": (
                        mokafaa_redemption_serializer.transaction_obj.
                        brand_calculations),
                    "order_reference": transaction_order_reference,
                    "transaction_id": str(
                        mokafaa_redemption_serializer.transaction_obj.
                        transaction_id),
                    "language_code": (
                        mokafaa_redemption_serializer.transaction_obj.language
                    ),
                    "currency": (
                        mokafaa_redemption_serializer.transaction_obj.currency
                    ),
                    "amount_in_aed": str(
                        mokafaa_redemption_serializer.transaction_obj.
                        amount_in_aed),
                    "card_number": validated_data.get("card_number"),
                    "card_expiry": validated_data.get("card_expiry"),
                }
            )
            mokafaa_service = MokafaServiceManager()
            response_data, code = mokafaa_service.redeem_points(
                points_redemption_data)
            if response_data and code == mokafaa_service.SUCCESS:
                formatted_res = mokafaa_response_formatter(response_data, code)
                data = self.response_obj.get_success_dict(
                    code=code,
                    success_dict=formatted_res
                )
                return Response(data, status=status.HTTP_200_OK)
            else:
                """Need to show error message to Front end
                so data = self.response_obj.get_error_dict(error_code=code)
                """
                return Response(response_data,
                                status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error("Exception {}".format(str(e)), exc_info=True)
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)


def mokafaa_response_formatter(data, code):
    """
    Mokafaa Response format method
    """

    mokafaa_response = data.get('mokafaa_response')
    errors = data.get('errors')
    is_success = data.get(IS_SUCCESS)
    if mokafaa_response:
        message = mokafaa_response.get("reason")
        data['code'] = code
        data['reason'], data['message'] = message, message
        data[IS_SUCCESS] = is_success
        data.pop('mokafaa_response', None)
    if errors:
        errors['message'] = COMMON_ERROR_MESSAGE_EN
        errors['code'] = code

    if not data.get('message'):
        data['message'] = COMMON_ERROR_MESSAGE_EN
        data['code'] = COMMON_ERROR_MESSAGE_EN_CODE
    return data
