import json
import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.messages import COMMON_ERROR_MESSAGE_EN
from core.response_messages import YouPayResponse
from core.utils import decrypt_string
from integrations.constants import NEQATY_CLIENT_CODE
from integrations.v1.gateway_clients.neqaty_service import (
    NeqatyServiceManager)
from integrations.v1.serializers.neqaty_serializer import (
    NeqatyRedemptionSerializer)
from payments.constants import PAYMENT_METHOD_NEQATY, \
    PAYMENT_METHOD_NEQATY_AND_CARD
from services.v1.views.common import YouPayTransactionCRUD

logger = logging.getLogger(__name__)


class NeqatyPointBalanceAPIView(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        """
        request for handling Neqaty generate otp api
        """
        logger.info("NeqatyPointBalanceAPIView request data : {}".format(
            request.data))

        try:
            mobile_number = request.data.get('mobile_number')
            transaction_id = request.data.get('transaction_id')
            transaction_obj = self.get_youpay_transaction_data(
                decrypt_string(transaction_id))
            if transaction_obj:
                payload = {
                    'client_code': NEQATY_CLIENT_CODE,
                    'invoice_id': transaction_obj.invoice_id,
                    'platform': transaction_obj.platform,
                    'amount': str(transaction_obj.base_amount),
                    'customer_name': transaction_obj.customer_name,
                    'customer_email': transaction_obj.customer_email,
                    "msisdn": mobile_number,
                    "transaction_obj": transaction_obj,
                    "currency": transaction_obj.currency
                }
                neqaty_service = NeqatyServiceManager()
                response_data, code = neqaty_service.point_balance(
                    payload)

                if response_data and code == self.response_obj.SUCCESS:
                    data = self.response_obj.get_success_dict(
                        code=code,
                        success_dict=response_data
                    )
                    return Response(data, status=status.HTTP_200_OK)
                else:
                    return Response(response_data,
                                    status=status.HTTP_400_BAD_REQUEST)

            else:
                data = self.response_obj.get_error_dict(
                    error_code=self.response_obj.TRANSACTION_NOT_FOUND)
                logger.error(
                    "NeqatyPointBalanceAPIView : Transaction not found for {}"
                    "".format(transaction_id))
                return Response(data, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            logger.error(
                "Exception occurred on NeqatyPointBalanceAPIView : {}".format(
                    str(e)), exc_info=True)
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)


class NeqatyGenerateOTPAPIView(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        """
        request for handling neqaty generate otp api
        """
        logger.info("NeqatyGenerateOTPAPIView request data : {}".format(
            request.data))

        try:
            transaction_id = request.data.get('transaction_id')
            transaction_obj = self.get_youpay_transaction_data(
                decrypt_string(transaction_id))
            redeem_code = request.data.get("redeem_code")
            payload = {
                'client_code': NEQATY_CLIENT_CODE,
                'reference_id': transaction_obj.payment_reference,
                'redeem_code': redeem_code,
                'transaction_obj': transaction_obj
            }
            neqaty_service = NeqatyServiceManager()
            response_data, code = neqaty_service.generate_otp(payload)

            if response_data and code == self.response_obj.SUCCESS:
                data = self.response_obj.get_success_dict(
                    code=code,
                    success_dict=response_data
                )
                return Response(data, status=status.HTTP_200_OK)
            else:
                data = self.response_obj.get_error_dict(error_code=code)
                return Response(data, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(
                "Exception occurred on NeqatyGenerateOTPAPIView : {}".format(
                    str(e)), exc_info=True)
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)


class NeqatyRedeemPointsAPIView(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        """
        request for handling neqaty points redemption api
        1.full redemption
        2.partial redemption
        """
        logger.info(
            "NeqatyRedeemPointsAPIView API triggered, request data"
            ": {}".format(request.data))

        try:
            transaction_id = request.data.get('transaction_id')
            transaction_obj = self.get_youpay_transaction_data(
                decrypt_string(transaction_id))

            neqaty_redemption_serializer = NeqatyRedemptionSerializer(
                data=request.data, context={'request': request})

            neqaty_redemption_serializer.is_valid(raise_exception=True)
            validated_data = neqaty_redemption_serializer.data

            points_redemption_data = validated_data

            points_redemption_data.update(
                {
                    "transaction_obj": transaction_obj,
                    'client_code': NEQATY_CLIENT_CODE,
                    "encrypted_id": request.data.get('transaction_id'),
                    "reference_id": transaction_obj.payment_reference,
                    "customer_name": request.data.get('customer_name')
                }
            )
            neqaty_service = NeqatyServiceManager()
            response_data, code = neqaty_service.redeem_points(
                points_redemption_data)
            if response_data and code == self.response_obj.SUCCESS:
                data = self.response_obj.get_success_dict(
                    code=code,
                    success_dict=response_data
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


class NeqatyVerify(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def get(self, request, *args, **kwargs):
        neqaty_service = NeqatyServiceManager()
        payment_data = {
            'transaction_id': request.query_params.get('id'),
            'redemption_partner': request.query_params.get(
                'redemption_partner'),
            'redemption_reference_id': request.query_params.get(
                'redemption_reference_id'),
            'cko-session-id': request.query_params.get(
                'cko-session-id')}
        response, transaction_obj = neqaty_service.verification(payment_data)
        transaction_id = (
            transaction_obj.transaction_id if transaction_obj
            else None)
        if response:
            logger.info("NeqatyVerify Response {}".format(response))
            if response.get('is_success') and response.get('is_redirect'):
                logger.info(
                    "Neqaty Verification successful, payment status true for"
                    " transaction {}".format(transaction_id))

                response['message'] = self.response_obj.PAYMENT_SUCCESS
                code = self.response_obj.B2CPAYBACK_VERIFICATION_SUCCESS
                response = self.format_b2c_response(response, code)
            else:
                message = (
                    "couldnt process Neqaty Verification for transaction id {}"
                    ", response : {}".format(transaction_id, response))

                logger.error(message)

                code = self.response_obj.NEQATY_VERIFICATION_FAILED_TO_PROCESS
                response = self.format_b2c_response(response, code)
            return Response(response, status=status.HTTP_200_OK)
        else:
            try:
                response_text = json.loads(response.text)
                resp_code = response_text.get('code', False)
                message = response_text.get('message', None)
                response = {'errors': {
                    'code': resp_code, 'message': message}}
                code = self.response_obj.NEQATY_VERIFICATION_FAILED
                logger.error("Verification failed for : {}, reason : {}"
                             .format(transaction_id, response))
                response = self.format_b2c_response(response, code)

            except Exception as e:
                logger.error(
                    "Exception occurred for transaction id : {}, "
                    "reason : {}".format(transaction_id, str(e)))

                response = {'errors': {
                    'code': "400",
                    'message': "Unable to process verification"}
                }
                code = self.response_obj.NEQATY_VERIFICATION_EXCEPTION
                response = self.format_b2c_response(response, code)
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

    def format_b2c_response(self, data, code):

        errors = data.get('errors', None)
        results = data.get('results', None)

        if results:
            data.pop('results')
            data['code'] = code
            data['message'] = self.response_obj.MESSAGE.get(code)

        if errors:
            errors['message'] = COMMON_ERROR_MESSAGE_EN
            errors['code'] = code

        return data


class UpdateNeqatyPhoneNumber(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        try:
            transaction_id = request.data.get('transaction_id')
            neqaty_phone_number = request.data.get('neqaty_phone_number')

            transaction_obj = self.get_youpay_transaction_data(
                decrypt_string(transaction_id))
            if transaction_obj:
                data = {
                    'transaction_id': transaction_obj.transaction_id,
                    'points_collected_mobile_number': neqaty_phone_number,
                    'points_collection_enabled_program': PAYMENT_METHOD_NEQATY,
                    'point_collection_enabled': True
                }
                neqaty_service = NeqatyServiceManager()
                result = neqaty_service.update_points_collected_mobile_number(
                    data)
                if result:
                    data = self.response_obj.get_success_dict(
                        code=self.response_obj.NEQATY_PHONE_NUMBER_SAVED,
                        success_dict={}
                    )
                    return Response(data, status=status.HTTP_200_OK)
                else:
                    logger.error("Couldn't Update Neqaty phone number for {}"
                                 "".format(transaction_obj.transaction_id))
                    data = self.response_obj.get_error_dict(
                        error_code=(
                            self.response_obj.NEQATY_PHONE_NUMBER_SAVE_FAILED))
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


class NeqatyCollectPointsAPIView(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        """
        request for handling neqaty collect points api
        """
        try:
            transaction_id = request.data.get('transaction_id')

            transaction_obj = self.get_youpay_transaction_data(
                decrypt_string(transaction_id))
            if transaction_obj:

                response_data, code = self.collect_reward_point(
                    transaction_obj)
                logger.info(
                    "Reward Point(Collect Points) API response {}, code : {}"
                    .format(response_data, code))
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
                    "NeqatyCollectPointsAPIView : Transaction not found for {}"
                    "".format(transaction_id))
                return Response(data, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)

    def collect_reward_point(self, transaction_obj):
        if transaction_obj.payment_method in [
            PAYMENT_METHOD_NEQATY,
            PAYMENT_METHOD_NEQATY_AND_CARD
        ]:
            paid_amount = transaction_obj.payable_amount
        else:
            paid_amount = transaction_obj.amount

        data = {
            "mobile_number": transaction_obj.points_collected_mobile_number,
            "customer_email": transaction_obj.customer_email,
            "customer_name": transaction_obj.customer_name,
            "invoice_id": transaction_obj.invoice_id,
            "gateway_reference": transaction_obj.payment_reference,
            "currency": transaction_obj.currency,
            "client_code": NEQATY_CLIENT_CODE,
            "transaction_obj": transaction_obj,
            "amount": int(paid_amount),
            "platform": transaction_obj.platform,
        }

        logger.info("NeqatyCollectPointsAPIView request data : {}".format(
            data))

        response_obj = YouPayResponse()

        if transaction_obj.earned_point:
            '''if already rewarded'''
            logger.info(
                "Failed for Reward point, reward already collected "
                "for ({}), rewarded point {}".format(
                    transaction_obj.transaction_id,
                    transaction_obj.earned_point))
            return None, response_obj.NEQATY_ALREADY_COLLECTED, transaction_obj.earned_point

        neqaty_service = NeqatyServiceManager()
        response_data, code = neqaty_service.collect_points(
            data)

        return response_data, code
