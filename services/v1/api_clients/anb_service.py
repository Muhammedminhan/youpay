import copy
import json
import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.messages import (IS_SUCCESS, COMMON_ERROR_MESSAGE_EN,
                           COMMON_ERROR_MESSAGE_EN_CODE)
from core.response_messages import YouPayResponse
from integrations.v1.gateway_clients.anb_service import AnbServiceManager
from integrations.v1.serializers.anb_serializer import AnbRedemptionSerializer
from services.v1.serializers.payment_request import AnbOTPSerializer
from services.v1.views.common import YouPayTransactionCRUD

logger = logging.getLogger(__name__)


class AnbGenerateOTPAPIView(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        """
        Post method for handling AnB generate otp api.
        Request:
        - transaction_id (str): The ID of the transaction to process.
        - mobile_number or cif_number (str): The mobile or identifier number
          used for AnB point redemption.

        Response:
        - 200: OTP successfully generated with `success_dict` in the response.
        - 400: Invalid input or service failure with an error message.
        - 404: Transaction not found.
        """
        transaction_id = request.data.get('transaction_id')
        logger.info("AnbGenerateOTPAPIView request data : {} for "
                    "transaction id {}".format(
                     request.data, transaction_id))
        try:
            anb_otp_serializer = AnbOTPSerializer(data=request.data)
            if anb_otp_serializer.is_valid(raise_exception=True):
                transaction_obj = anb_otp_serializer.transaction_obj
                validated_data = anb_otp_serializer.validated_data
                # Dictionary unpacking to add the dynamic field
                mobile_or_cif = {mobile_or_cif_key: mobile_or_cif_value for
                                 mobile_or_cif_key, mobile_or_cif_value in
                                 validated_data.items() if mobile_or_cif_key
                                 in ['mobile_number', 'cif_number']}
                payload = {'request_data': {
                    'transaction_obj': transaction_obj,
                    **mobile_or_cif,
                }}
                anb_service = AnbServiceManager()
                response_data, code = anb_service.generate_otp(payload)

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
            logger.error("Exception occurred on AnbGenerateOTPAPIView : {} "
                         "for transaction id {}"
                         .format(str(e), transaction_id), exc_info=True)
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)


class AnbRedeemPointsAPIView(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        """
        request for handling anb points redemption api
        1.full redemption
        2.partial redemption

        Args:
            request: The HTTP request containing redemption details.
        Returns:
                Response: A success or error response based on the
                redemption result.
        """
        try:
            request_data = copy.deepcopy(request.data)
            if request_data.get("cvv"):
                request_data["cvv"] = "***"
            logger.info("AnbRedeemPointsAPIView triggered for request "
                        "data: {}".format(request_data))
            anb_redemption_serializer = AnbRedemptionSerializer(
                data=request.data, context={'request': request})
            anb_redemption_serializer.is_valid(raise_exception=True)
            validated_data = anb_redemption_serializer.data
            points_redemption_data = validated_data
            transaction_obj = anb_redemption_serializer.transaction_obj
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
                    "card_expiry": validated_data.get("card_expiry"),
                    "checkout_reference": transaction_obj.additional_reference
                }
            )
            anb_service = AnbServiceManager()
            response_data, code = anb_service.redeem_points(
                points_redemption_data)
            if response_data and code == anb_service.SUCCESS:
                formatted_res = anb_response_formatter(response_data, code)
                data = self.response_obj.get_success_dict(
                    code=code,
                    success_dict=formatted_res
                )
                return Response(data, status=status.HTTP_200_OK)
            else:
                return Response(response_data,
                                status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error("Exception {}".format(str(e)), exc_info=True)
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)


class AnbVerify(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def get(self, request, *args, **kwargs):
        """
        Used for verification of payment transaction.

        Args:
            request: The HTTP request object containing transaction details.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments, including transaction
                      related parameters.
        Returns:
            Response: A formatted response indicating the verification result.
        """
        anb_service = AnbServiceManager()
        payment_data = {
            'transaction_id': request.query_params.get('id'),
            'redemption_partner': request.query_params.get(
                'redemption_partner'),
            'redemption_reference_id': request.query_params.get(
                'redemption_reference_id'),
            'cko-session-id': request.query_params.get(
                'cko-session-id')
        }
        response, transaction_obj = anb_service.verification(payment_data)
        transaction_id = (transaction_obj.transaction_id if transaction_obj
                          else None)
        if response:
            logger.info("AnbVerify Response {} for transaction id {}".format(
                response, transaction_id))
            if response.get('is_success') and response.get('is_redirect'):
                logger.info(
                    "Anb Verification successful, payment status true for"
                    " transaction {}".format(transaction_id))

                code = self.response_obj.B2CPAYBACK_VERIFICATION_SUCCESS
                response = self.format_b2c_response(response, code)
            else:
                message = (
                    "couldnt process Anb Verification for transaction id {}, "
                    "response : {}".format(transaction_id, response))
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
                code = self.response_obj.ANB_VERIFICATION_FAILED
                logger.error("Verification failed for : {}, reason : {}"
                             .format(transaction_id, response))
                response = self.format_b2c_response(response, code)
            except Exception as e:
                logger.error("Exception occurred for transaction id : {}, "
                             "reason : {}".format(
                                transaction_id, str(e)))
                response = {'errors': {
                    'code': "400",
                    'message': "Unable to process verification"}
                }
                code = self.response_obj.ANB_VERIFICATION_EXCEPTION
                response = self.format_b2c_response(response, code)
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

    def format_b2c_response(self, data, code):
        """
        Formats the response for B2C payment verification.

        Args:
            data: The response dictionary containing payment verification
            details.
            code: Payment verification code.

        Returns:
            data: Formatted response dictionary.
        """
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


def anb_response_formatter(data, code):
    """
    AnB Response format method
    Args:
        data (dict): The response data from the AnB service.
        code (int): The response status code.
    Returns:
        dict: The formatted response with a message, code, and success status.
    """
    anb_response = data.get('anb_response')
    errors = data.get('errors')
    is_success = data.get(IS_SUCCESS)
    if anb_response:
        message = anb_response.get("reason")
        data['code'] = code
        data['reason'], data['message'] = message, message
        data[IS_SUCCESS] = is_success
        data.pop('anb_response', None)
    if errors:
        errors['message'] = COMMON_ERROR_MESSAGE_EN
        errors['code'] = code

    if not data.get('message'):
        data['message'] = COMMON_ERROR_MESSAGE_EN
        data['code'] = COMMON_ERROR_MESSAGE_EN_CODE
    return data


def get_calculated_youpay_transaction_data_with_anb_balance(
        transaction_obj):
    """
    To replace the additional_data with the anb balance calculation response
    from the anb service.

    Args:
        transaction_obj: Payment transaction object.

    Returns:
        youpay_update_data (dict): A dictionary with calculated transaction
        amounts.

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
