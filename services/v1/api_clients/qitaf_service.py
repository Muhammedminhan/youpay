import json
import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.constants import QITAF_REWARD_POINT_MIN_AMT
from core.messages import (IS_SUCCESS, COMMON_ERROR_MESSAGE_EN,
                           COMMON_ERROR_MESSAGE_EN_CODE)
from core.response_messages import YouPayResponse
from core.utils import decrypt_string
from integrations.common import update_brand_details
from integrations.constants import QITAF_CLIENT_CODE
from integrations.v1.gateway_clients.qitaf_service import QitafServiceManager
from integrations.v1.serializers.qitafpg_serializer import (
    QitafRedemptionSerializer)
from payments.constants import (PAYMENT_METHOD_QITAF,
                                PAYMENT_METHOD_QITAFAND_CARD)
from services.v1.serializers.payment_request import QitafOTPSerializer
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
                is_updated, brand_details = update_brand_details(
                    transaction_obj)
                if not is_updated:
                    data = self.response_obj.get_error_dict(
                        error_code=(
                            self.response_obj.QITAF_PHONE_NUMBER_SAVE_FAILED))
                    return Response(data,
                                    status=status.HTTP_400_BAD_REQUEST)
                data = {
                    'transaction_id': transaction_obj.transaction_id,
                    'qitaf_phone_number': qitaf_phone_number,
                    'points_collected_mobile_number': qitaf_phone_number,
                    'points_collection_enabled_program': PAYMENT_METHOD_QITAF,
                    'point_collection_enabled': True,
                    'is_qitaf_enabled': True,
                    "brand_details": brand_details
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
                data = self.response_obj.get_error_dict(
                    error_code=self.response_obj.TRANSACTION_NOT_FOUND)
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
        logger.info("QitafGenerateOTPAPIView request data : {}".format(
            request.data))

        try:
            mobile_number = request.data.get('mobile_number')
            otp_serializer = QitafOTPSerializer(data=request.data)
            if otp_serializer.is_valid(raise_exception=True):
                transaction_obj = otp_serializer.transaction_obj
                payload = {'request_data': {
                    'transaction_obj': transaction_obj,
                    "mobile_number": mobile_number
                }}
                qitaf_service = QitafServiceManager()
                response_data, code = qitaf_service.generate_otp(payload)

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
                "Exception occurred on QitafGenerateOTPAPIView : {}".format(
                    str(e)), exc_info=True)
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)


class QitafCollectPointsAPIView(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        """
        request for handling qitaf collect points api
        """
        try:
            transaction_id = request.data.get('transaction_id')

            transaction_obj = self.get_youpay_transaction_data(
                decrypt_string(transaction_id))
            if transaction_obj:

                response_data, code, qitaf_reward = self.collect_reward_point(
                    transaction_obj)
                logger.info(
                    "Reward Point(Collect Points) API response {}, code : {},"
                    " rewarded : {}".format(response_data, code,
                                            qitaf_reward))
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
            else:
                data = self.response_obj.get_error_dict(
                    error_code=self.response_obj.TRANSACTION_NOT_FOUND)
                logger.error(
                    "QitafCollectPointsAPIView : Transaction not found for {}"
                    "".format(transaction_id))
                return Response(data, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)

    def collect_reward_point(self, transaction_obj):
        if transaction_obj.payment_method in [
            PAYMENT_METHOD_QITAF,
            PAYMENT_METHOD_QITAFAND_CARD
        ]:
            paid_amount = transaction_obj.brand_calculations.get(
                'sum_card_payment_amount', 0)
        else:
            paid_amount = float(transaction_obj.amount)

        data = {
            "mobile_number": transaction_obj.qitaf_phone_number,
            "transaction_obj": transaction_obj,
            "amount": int(paid_amount),
            "platform": transaction_obj.platform,
        }

        logger.info("QitafCollectPointsAPIView request data : {}".format(
            data))

        response_obj = YouPayResponse()

        if transaction_obj.earned_point:
            '''if already rewarded'''
            logger.info(
                "Failed for Reward point, reward already collected "
                "for ({}), rewarded point {}".format(
                    transaction_obj.transaction_id,
                    transaction_obj.earned_point))
            return None, response_obj.QITAF_ALREADY_COLLECTED, transaction_obj.earned_point

        if data["amount"] < QITAF_REWARD_POINT_MIN_AMT:
            logger.info("Qitaf RewardPoint Failed for {} ".format(
                transaction_obj.transaction_id,
            ))
            return None, response_obj.QITAF_REWARD_POINT_MIN_AMT_NOT_MET, None

        qitaf_service = QitafServiceManager()
        response_data, code = qitaf_service.collect_points(
            data)

        return response_data, code, None


class QitafRedeemPointsAPIView(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        """
        request for handling qitaf points redemption api
        1.full redemption
        2.partial redemption
        """
        try:
            logger.info("QitafRedeemPointsAPIView API triggered, request data"
                        ": {}".format(request.data))
            qitaf_redemption_serializer = QitafRedemptionSerializer(
                data=request.data, context={'request': request})

            qitaf_redemption_serializer.is_valid(raise_exception=True)
            validated_data = qitaf_redemption_serializer.data

            points_redemption_data = validated_data

            selected_amount_in_req = request.data.get("selected_amount")
            transaction_order_reference = (
                qitaf_redemption_serializer.transaction_obj.order_reference)
            points_redemption_data.update(
                {
                    "transaction_obj": qitaf_redemption_serializer.transaction_obj,
                    "referance_id": qitaf_redemption_serializer.transaction_obj.payment_reference,
                    "pin_number": validated_data.get('pin_number'),
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
                        qitaf_redemption_serializer.transaction_obj.brand_calculations),
                    "order_reference": transaction_order_reference
                }
            )
            qitaf_service = QitafServiceManager()
            response_data, code = qitaf_service.redeem_points(
                points_redemption_data)
            if response_data and code == 1000:
                formatted_res = qitaf_response_formatter(response_data, code)
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


class QitafVerify(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def get(self, request, *args, **kwargs):
        manager_obj = QitafServiceManager()
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
            logger.info("QitafVerify Response {}".format(response))
            if response.get('is_success') and response.get('is_redirect'):
                logger.info(
                    "Qitaf Verification successful, payment status true for"
                    " transaction {}".format(transaction_id))

                code = self.response_obj.B2CPAYBACK_VERIFICATION_SUCCESS
                response = self.format_b2c_response(response, code)
            else:
                message = (
                    "couldnt process qitaf Verification for transaction id {}"
                    ", response : {}".format(transaction_id, response))

                logger.error(message)

                code = self.response_obj.QITAF_VERIFICATION_FAILED_TO_PROCESS
                response = self.format_b2c_response(response, code)
            return Response(response, status=status.HTTP_200_OK)
        else:
            try:
                response_text = json.loads(response.text)
                resp_code = response_text.get('code', False)
                message = response_text.get('message', None)
                response = {'errors': {
                    'code': resp_code, 'message': message}}
                code = self.response_obj.QITAF_VERIFICATION_FAILED
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
                code = self.response_obj.QITAF_VERIFICATION_EXCEPTION
                response = self.format_b2c_response(response, code)
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

    def format_b2c_response(self, data, code):

        errors = data.get('errors', None)
        results = data.get('results', None)

        data['message'] = self.response_obj.MESSAGE.get(code)
        if results:
            data.pop('results')
            data['code'] = code

        if errors:
            errors['message'] = COMMON_ERROR_MESSAGE_EN
            errors['code'] = code

        return data


class CalculateQitafBalance(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        try:
            transaction_id = request.data.get('transaction_id')
            selected_amount = request.data.get('selected_amount')
            transaction_obj = self.get_youpay_transaction_data(
                decrypt_string(transaction_id))
            if transaction_obj:
                payload = {
                    'transaction_obj': transaction_obj,
                    "selected_amount": selected_amount,
                    "client_code": QITAF_CLIENT_CODE
                }

                qitaf_service = QitafServiceManager()
                response_data, code = qitaf_service.calculate_qitaf_balance(
                    payload)

                logger.info("Reward Point(Collect Points) API response {}, "
                            "code : {}".format(response_data, code, ))
                if response_data:

                    data = self.response_obj.get_success_dict(
                        code=code,
                        success_dict=response_data
                    )
                    return Response(data, status=status.HTTP_200_OK)
                else:
                    data = self.response_obj.get_error_dict(error_code=code)
                    return Response(data,
                                    status=status.HTTP_400_BAD_REQUEST)
            else:
                data = self.response_obj.get_error_dict(
                    error_code=self.response_obj.TRANSACTION_NOT_FOUND)
                logger.error(
                    "QitafCollectPointsAPIView : Transaction not found for {}"
                    "".format(transaction_id))
                return Response(data, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)


def get_calculated_youpay_transaction_data_with_qitaf_balance(
        transaction_obj):
    """
    The idea is to replace the additional_data with the qitaf balance
     calculation response from the qitaf service
    """

    brand_calculations = transaction_obj.brand_calculations
    youpay_update_data = {}
    if brand_calculations:
        amount = brand_calculations.get('sum_net_amount', None)
        base_amount = brand_calculations.get('sum_gift_base_value',
                                             None)
        redeemed_amount = brand_calculations.get(
            'sum_redemption_points', None)
        redeemed_point = brand_calculations.get(
            'sum_redemption_points', None)
        payable_amount = brand_calculations.get(
            'sum_card_payment_amount', None)
        service_fee = brand_calculations.get(
            'sum_applied_service_charge', None)
        vat_amount = brand_calculations.get('sum_applied_vat', None)

        youpay_update_data = {
            'redeemed_amount': redeemed_amount,
            'redeemed_points': redeemed_point,
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


def qitaf_response_formatter(data, code):
    """
    Qitaf Response format method
    """

    qitaf_response = data.get('qitaf_response')
    errors = data.get('errors')
    is_success = data.get(IS_SUCCESS)
    if qitaf_response:
        message = qitaf_response.get("reason")
        data['code'] = code
        data['reason'], data['message'] = message, message
        data[IS_SUCCESS] = is_success
        data.pop('qitaf_response', None)
    if errors:
        errors['message'] = COMMON_ERROR_MESSAGE_EN
        errors['code'] = code

    if not data.get('message'):
        data['message'] = COMMON_ERROR_MESSAGE_EN
        data['code'] = COMMON_ERROR_MESSAGE_EN_CODE
    return data
