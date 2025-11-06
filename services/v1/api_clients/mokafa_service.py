import copy
import json
import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.messages import (IS_SUCCESS, COMMON_ERROR_MESSAGE_EN,
                           COMMON_ERROR_MESSAGE_EN_CODE)
from core.response_messages import YouPayResponse
from core.utils import decrypt_string
from integrations.common import update_brand_details
from integrations.v1.gateway_clients.mokafa_service import (
    MokafaServiceManager)
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
            request_data = copy.deepcopy(request.data)
            if request_data.get("cvv"):
                request_data["cvv"] = "***"
            logger.info("MokafaaRedeemPointsAPIView API triggered, request "
                        "data: {}".format(request_data))
            mokafaa_redemption_serializer = MokafaaRedemptionSerializer(
                data=request.data, context={'request': request})

            mokafaa_redemption_serializer.is_valid(raise_exception=True)
            validated_data = mokafaa_redemption_serializer.data

            points_redemption_data = validated_data
            transaction_obj = mokafaa_redemption_serializer.transaction_obj

            selected_amount = str(int(transaction_obj.redeemed_amount))
            checkout_amount = str(float(transaction_obj.payable_amount))
            customer_name = request.data.get("customer_name")
            transaction_order_reference = transaction_obj.order_reference
            points_redemption_data.update(
                {
                    "transaction_obj": transaction_obj,
                    "referance_id": transaction_obj.payment_reference,
                    "one_time_password": validated_data.get('pin_number'),
                    "selected_amount": selected_amount,
                    "checkout_amount": checkout_amount,
                    "is_save_user_token": validated_data.get(
                        'is_save_user_token'),
                    "customer_name": customer_name,
                    "cvv": validated_data.get('cvv'),
                    "token": validated_data.get('token'),
                    "token_type": validated_data.get('token_type'),
                    "encrypted_id": request.data.get('transaction_id'),
                    "brand_calculations": transaction_obj.brand_calculations,
                    "order_reference": transaction_order_reference,
                    "transaction_id": str(transaction_obj.transaction_id),
                    "language_code": transaction_obj.language,
                    "currency": transaction_obj.currency,
                    "amount_in_aed": str(transaction_obj.amount_in_aed),
                    "card_number": validated_data.get("card_number"),
                    "card_expiry": validated_data.get("card_expiry")
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


class MokafaaVerify(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def get(self, request, *args, **kwargs):
        manager_obj = MokafaServiceManager()
        payment_data = {
            'transaction_id': request.query_params.get('id'),
            'redemption_partner': request.query_params.get(
                'redemption_partner'),
            'redemption_reference_id': request.query_params.get(
                'redemption_reference_id'),
            'cko-session-id': request.query_params.get(
                'cko-session-id')}
        response, transaction_obj = manager_obj.verification(payment_data)
        transaction_id = (transaction_obj.transaction_id if transaction_obj
                          else None)
        if response:
            logger.info("MokafaaVerify Response {}".format(response))
            if response.get('is_success') and response.get('is_redirect'):
                logger.info(
                    "Mokafaa Verification successful, payment status true for"
                    " transaction {}".format(transaction_id))

                code = self.response_obj.B2CPAYBACK_VERIFICATION_SUCCESS
                response = self.format_b2c_response(response, code)
            else:
                message = (
                    "couldnt process Mokafaa Verification for transaction id"
                    " {}, response : {}".format(transaction_id, response))

                logger.error(message)

                response = self.format_b2c_response(response, None)
            return Response(response, status=status.HTTP_200_OK)
        else:
            try:
                response_text = json.loads(response.text)
                resp_code = response_text.get('code', False)
                message = response_text.get('message', None)
                response = {'errors': {
                    'code': resp_code, 'message': message}}
                code = self.response_obj.MOKAFAA_VERIFICATION_FAILED
                logger.error("Verification failed for : {}, reason : {}"
                             .format(transaction_id, response))
                response = self.format_b2c_response(response, code)

            except Exception as e:
                logger.error("Exception occurred for transaction id : {}, "
                             "reason : {}".format(transaction_id, str(e)))

                response = {'errors': {
                    'code': "400",
                    'message': "Unable to process verification"}
                }
                code = self.response_obj.MOKAFAA_VERIFICATION_EXCEPTION
                response = self.format_b2c_response(response, code)
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

    def format_b2c_response(self, data, code):

        errors = data.get('errors', None)
        results = data.get('results', None)

        data['message'] = (self.response_obj.MESSAGE.get(
            code) if code else data.get('message', None))
        if results:
            data.pop('results')
            data['code'] = code

        if errors:
            errors['message'] = COMMON_ERROR_MESSAGE_EN
            errors['code'] = code

        return data


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


def get_calculated_youpay_transaction_data_with_mokafaa_balance(
        transaction_obj):
    """
    The idea is to replace the additional_data with the mokafaa balance
     calculation response from the mokafaa service
    """

    brand_calculations = transaction_obj.brand_calculations
    youpay_update_data = {}
    if brand_calculations:
        amount = brand_calculations.get('sum_net_amount', None)
        base_amount = brand_calculations.get('sum_gift_base_value',
                                             None)
        redeemed_amount = brand_calculations.get(
            'sum_redemption_points', None)
        payable_amount = brand_calculations.get(
            'sum_card_payment_amount', None)
        service_fee = brand_calculations.get(
            'sum_applied_service_charge', None)
        vat_amount = brand_calculations.get('sum_applied_vat', None)

        youpay_update_data = {
            'redeemed_amount': redeemed_amount,
            'amount': amount,
            'payable_amount': payable_amount,
            'service_fee': service_fee,
            'base_amount': base_amount,
            'VAT_amount': vat_amount,
            'payment_method': transaction_obj.payment_method,
        }
    else:
        logger.error("Brand calculation is empty for transaction {}".format(
            transaction_obj.transaction_id
        ))

    return youpay_update_data
