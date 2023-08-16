import json
import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.constants import Qitaf_response_object, QITAF_REWARD_POINT_MIN_AMT
from core.messages import IS_SUCCESS, COMMON_ERROR_MESSAGE_EN
from core.response_messages import YouPayResponse
from core.utils import decrypt_string
from integrations.v1.gateway_clients.qitaf_service import QitafServiceManager
from integrations.v1.serializers.qitafpg_serializer import (
    QitafRedemptionSerializer)
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
                response_flag, qitaf_response_data = get_qitaf_response_message(
                    response_data, code)

                if response_data and code == self.response_obj.SUCCESS:
                    data = self.response_obj.get_success_dict(
                        code=code,
                        success_dict=response_data
                    )
                    return Response(data, status=status.HTTP_200_OK)
                elif response_flag:  # todo Remove after testing
                    return Response(qitaf_response_data,
                                    status=status.HTTP_400_BAD_REQUEST)
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


def get_qitaf_response_message(response_data, code):
    """
    ERROR RESPONSE OBJECT
    {
        'error':{
            'message': 'QitafNot Found Or Available',
            'status': False,
            'response_data':{
                'no_response': False,
                'response_code': '1019',
                'response_text': 'QitafNot Found Or Available'
            }
        }
    }
    """
    response_flag = False
    error_obj = response_data.get('error', {})
    if error_obj:
        response_flag = True
        qitaf_response_data = error_obj.get('response_data', {})
        if qitaf_response_data:
            response_code = qitaf_response_data.get('response_code')
            result_response = {
                "errors": {
                    "message": Qitaf_response_object.get(response_code),
                    "qitaf_code": response_code,
                    "code": code

                }
            }
            response_data = result_response

    return response_flag, response_data


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

        data = {
            "mobile_number": transaction_obj.qitaf_phone_number,
            "transaction_obj": transaction_obj,
            "amount": int(transaction_obj.amount),
            "platform": transaction_obj.platform,
        }

        response_obj = YouPayResponse()
        if not (transaction_obj.is_qitaf_enabled and
                (not transaction_obj.earned_point)):
            '''if qitaf not enabled or already rewarded, this will check for
             already rewarded or qitaf is enabled'''

            logger.error(
                "Failed for Reward point, qitaf enabled ({}) or already "
                "rewarded ({}) {}".format(transaction_obj.is_qitaf_enabled,
                                          transaction_obj.transaction_id,
                                          transaction_obj.earned_point))
            return None, response_obj.QITAF_NOT_ENABLED, 0

        if data["amount"] < QITAF_REWARD_POINT_MIN_AMT:
            logger.info("Qitaf RewardPoint Failed for {} ".format(
                transaction_obj.transaction_id,
            ))
            return None, response_obj.QITAF_REWARD_POINT_MIN_AMT_NOT_MET, 0

        qitaf_service = QitafServiceManager()
        response_data, code = qitaf_service.collect_points(
            data)
        qitaf_reward = response_data.get("qitaf_response", {}).get(
            "reward_point", 0)

        self.update_youpay_transaction_data({
            "transaction_id": transaction_obj.transaction_id,
            "earned_point": qitaf_reward
        })

        return response_data, code, qitaf_reward


class QitafRedeemPointsAPIView(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        """
        request for handling qitaf points redemption api

        1.full redemption
        2.partial redemption

        body:

        amount through card -- can take remaining balance from transaction amt

        transaction_id
        selected_amount
        checkout_amount
        pin_number


        for card
        is_save_user_token
        card holder name
        token  -- generated card token (eg:tok_4ysrgucqwwpero7rasfcprtevq)

        for saved cards
        token  -- saved card token (eg:src_4ysrgucqwwpero7rasfcprtevq)
        cvv

        """
        try:
            logger.info("QitafRedeemPointsAPIView API triggered, request data"
                        ": {}".format(request.data))
            qitaf_redemption_serializer = QitafRedemptionSerializer(
                data=request.data, context={'request': request})

            qitaf_redemption_serializer.is_valid(raise_exception=True)
            validated_data = qitaf_redemption_serializer.data

            points_redemption_data = validated_data
            points_redemption_data.update(
                {
                    "transaction_obj": qitaf_redemption_serializer.transaction_obj,
                    "referance_id": qitaf_redemption_serializer.transaction_obj.payment_reference,
                    "pin_number": validated_data.get('pin_number'),
                    "selected_amount": validated_data.get('selected_amount'),
                    "checkout_amount": validated_data.get('checkout_amount'),
                    "is_save_user_token": validated_data.get(
                        'is_save_user_token'),
                    "customer_name": validated_data.get('customer_name'),
                    "cvv": validated_data.get('cvv'),
                    "token": validated_data.get('token'),
                    "token_type": validated_data.get('token_type'),
                    "encrypted_id": request.data.get('transaction_id')
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
                data = self.response_obj.get_error_dict(error_code=code)
                return Response(data, status=status.HTTP_400_BAD_REQUEST)
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
                response['message'] = "Transaction successful"
                code = self.response_obj.B2CPAYBACK_VERIFICATION_SUCCESS
                response = self.format_b2c_response(response, code)
            else:
                response["message"] = "Transaction failed"
                message = (
                    "couldnt process qitaf Verification for transaction id {}, "
                    "response : {}".format(transaction_id, response))

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

        errors = data.get('errors')
        results = data.get('results')

        if results:
            data.pop('results')
            data['code'] = code
            data['message'] = self.response_obj.MESSAGE.get(code)

        if errors:
            errors['message'] = COMMON_ERROR_MESSAGE_EN
            errors['code'] = code

        return data


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
        data['code'] = 11111
    return data
