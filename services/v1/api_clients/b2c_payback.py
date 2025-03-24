import json
import logging
from decimal import Decimal

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.constants import PAYMENT_GATEWAY_B2CPAYBACK
from core.messages import COMMON_ERROR_MESSAGE_EN
from core.response_messages import YouPayResponse
from core.utils import decrypt_string
from integrations.common import update_brand_details
from integrations.constants import ADCB_CLIENT_CODE, CLIENT_CODE_MAPPING
from integrations.messages import B2CPAYBACK_CHECKOUTPG_PAYMENT_FAILED_MESSAGE
from integrations.v1.gateway_clients.b2c_payback import B2CPaybackManager
from integrations.v1.gateway_clients.utils import (calculate_balance,
                                                   apply_offer_if_needed,
                                                   find_threshold_amount,
                                                   process_calculated_item_details)
from payments.constants import (
    PAYMENT_STATUS_AUTHORIZED, PAYMENT_METHOD_TOUCHPOINTS,
    PAYMENT_METHOD_TOUCHPOINTS_AND_CARD, PAYMENT_METHOD_ADCB_CARD_ONLY,
    PAYMENT_STATUS_PAID, PAYMENT_STATUS_PENDING
)
from services.v1.constants import B2C_PAYBACK_NO_RESPONSE_MESSAGE
from services.v1.views.common import YouPayTransactionCRUD

logger = logging.getLogger(__name__)


class B2CPaybackPointBalance(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        payback = B2CPaybackManager()
        response, transaction_obj, response_code = payback.get_point_balance(
            request.data)
        request_data = request.data
        try:
            if response_code == (
                    self.response_obj.CLIENT_TRANSACTION_VERIFICATION_FAILED):
                return Response(response, status=status.HTTP_200_OK)
            if response and response.status_code == 200:
                response_data = response.json()
                transaction_id = transaction_obj.transaction_id
                is_updated, brand_details = update_brand_details(
                    transaction_obj)
                self.update_youpay_transaction_data({
                    'transaction_id': transaction_id,
                    'payment_reference': response_data.get('reference_id',
                                                           None),
                    'payment_gateway': PAYMENT_GATEWAY_B2CPAYBACK,
                    'payment_status': PAYMENT_STATUS_PENDING,
                    'card_bin': request_data.get('card_no', "")[0:6],
                    'card_last4': request_data.get('card_no', "")[-4:],
                    'name_on_card': request_data.get('name_on_card', ""),
                    'available_amount': response_data.get('available_amount'),
                    'available_points': response_data.get('available_points')
                })
                offer_details = self.get_offer_details(transaction_obj)
                if offer_details:
                    program_offer = offer_details.get(ADCB_CLIENT_CODE)
                    offers = []
                    for offer in program_offer:
                        threshold_amount = find_threshold_amount(
                            offer, transaction_obj)
                        client_program_name = CLIENT_CODE_MAPPING.get(
                            ADCB_CLIENT_CODE,
                            "Redemption")
                        offer_data = {
                            "threshold_amount": threshold_amount,
                            "brand_code": offer["brand_code"],
                            "brand_name": offer["brand_name"],
                            "brand_logo": offer["brand_logo"],
                            "offer_text": offer["offer_text"],
                            "offer_error_message": (
                                f"Redeem at least SAR {threshold_amount} in "
                                f"{client_program_name} points to claim the offer")
                        }
                        offers.append(offer_data)
                    response_data.update({"offers": offers})
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                response_text = json.loads(response.text)
                resp_code = response_text.get('code', False)
                message = response_text.get('message', None)
                response = {'errors': {
                    'code': resp_code, 'message': message}}
        except Exception as e:
            logger.error("Failed response received from b2cpayback "
                         "point balance endpoint", exc_info=e)
            response = {'errors': {
                'code': "400", 'message': B2C_PAYBACK_NO_RESPONSE_MESSAGE}
            }
        return Response(response, status=status.HTTP_400_BAD_REQUEST)


class B2CPaybackAuthenticate(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        payback = B2CPaybackManager()
        response, transaction_obj = payback.authenticate_redemption(
            request.data)
        if response:
            apply_offer_if_needed(response, transaction_obj,
                                  response.get('brand_calculations'),
                                  ADCB_CLIENT_CODE)

            invoice_amount = transaction_obj.amount
            selected_amount = Decimal(request.data.get('selected_amount'))
            checkout_amount = Decimal(request.data.get('checkout_amount'))
            update_data = {
                'transaction_id': transaction_obj.transaction_id,
                'payment_gateway': PAYMENT_GATEWAY_B2CPAYBACK,
                'payment_status': PAYMENT_STATUS_AUTHORIZED,
                'is_gcc_card': True,
                'payable_amount': checkout_amount,
                'available_amount': transaction_obj.available_amount,
                'available_points': transaction_obj.available_points,
                'is_full_redemption': response.get('is_full_redemption'),
                'brand_calculations': response.get('brand_calculations')
            }

            if invoice_amount == selected_amount:  # full redemption
                update_data['payment_method'] = PAYMENT_METHOD_TOUCHPOINTS

            elif selected_amount > 0 and checkout_amount > 0:  # partial redemption
                update_data['payment_method'] = (
                    PAYMENT_METHOD_TOUCHPOINTS_AND_CARD)
                update_data['payment_scheme'] = request.data.get('card_type')

            else:  # full amount from card
                update_data['payment_method'] = PAYMENT_METHOD_ADCB_CARD_ONLY
                update_data['payment_scheme'] = request.data.get('card_type')

            self.update_youpay_transaction_data(update_data)
            return Response(response, status=status.HTTP_200_OK)
        else:
            try:
                response_text = json.loads(response.text)
                resp_code = response_text.get('code', False)
                message = response_text.get('message', None)
                response = {'errors': {
                    'code': resp_code, 'message': message}}
            except Exception as e:
                logger.error("Failed response received from b2cpayback "
                             "authenticate endpoint", exc_info=e)
                response = {'errors': {
                    'code': "400", 'message':
                        B2C_PAYBACK_NO_RESPONSE_MESSAGE}}
            return Response(response, status=status.HTTP_400_BAD_REQUEST)


class B2CPaybackRedemption(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        payback = B2CPaybackManager()
        response, transaction_obj = payback.point_redemption(request.data)
        transaction_id = (transaction_obj.transaction_id if transaction_obj
                          else None)
        if response:
            if response.get('results', {}).get('redemption_status') == True:
                update_data = {
                    'transaction_id': transaction_obj.transaction_id,
                    'payment_status': PAYMENT_STATUS_PAID,
                    'payment_reference': response.get(
                        'results', {}).get('reference_id'),
                    'approved': True,
                    "redeemed_amount": response.get(
                        'results', {}).get('redeemed_amount'),
                    "redeemed_points": response.get(
                        'results', {}).get('redeemed_points'),
                    'available_amount': response.get(
                        'results', {}).get('available_amount'),
                    'available_points': transaction_obj.available_points,
                    'payable_amount': transaction_obj.payable_amount,
                    'is_full_redemption': transaction_obj.is_full_redemption
                }
                self.update_youpay_transaction_data(update_data)
            else:
                logger.info(
                    "Point redemption not successful for transaction id "
                    "{}".format(transaction_id))
            return Response(response, status=status.HTTP_200_OK)
        else:
            try:
                response_text = json.loads(response.text)
                resp_code = response_text.get('code', False)
                message = response_text.get('message', None)
                response = {'errors': {
                    'code': resp_code, 'message': message}}
            except Exception as e:
                logger.error("Failed response received from b2cpayback "
                             "redemption endpoint", exc_info=e)
                response = {'errors': {
                    'code': "400", 'message': B2C_PAYBACK_NO_RESPONSE_MESSAGE}
                }
            return Response(response, status=status.HTTP_400_BAD_REQUEST)


class B2CPaybackVerify(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def get(self, request, *args, **kwargs):
        payback = B2CPaybackManager()
        request_params = request.query_params

        response, transaction_obj = payback.verification(request_params)
        transaction_id = (transaction_obj.transaction_id if transaction_obj
                          else None)
        if response:
            if response.get('results', {}).get('payment_status'):
                logger.info("Verification successful, payment status true for"
                            " transaction {}".format(transaction_id))
                code = self.response_obj.B2CPAYBACK_VERIFICATION_SUCCESS
                response = self.format_b2c_response(response, code)
            else:
                if not response.get("message"):
                    response["message"] = (
                        B2CPAYBACK_CHECKOUTPG_PAYMENT_FAILED_MESSAGE)
                message = (
                    "couldnt process b2c Verification for transaction id {}, "
                    "response : {}".format(transaction_id, response))

                logger.error(message)

                code = self.response_obj.B2CPAYBACK_VERIFICATION_FAILED_TO_PROCESS
                response = self.format_b2c_response(response, code)
            return Response(response, status=status.HTTP_200_OK)
        else:
            try:
                response_text = json.loads(response.text)
                resp_code = response_text.get('code', False)
                message = response_text.get('message', None)
                response = {'errors': {
                    'code': resp_code, 'message': message}}
                code = self.response_obj.B2CPAYBACK_VERIFICATION_FAILED
                logger.error("Verification failed for : {}, reason : {}"
                             .format(transaction_id, response))
                response = self.format_b2c_response(response, code)

            except Exception as e:
                logger.error("Exception occurred for transaction id : {}, "
                             "reason : {}".format(transaction_id, str(e)))

                response = {'errors': {
                    'code': "400", 'message': B2C_PAYBACK_NO_RESPONSE_MESSAGE}
                }
                code = self.response_obj.B2CPAYBACK_VERIFICATION_EXCEPTION
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


class CollectProgramManagement(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def get(self, request, pk):
        logger.info("CollectProgramManagement API called to get collect "
                    "program for transaction ID: {}".format(pk))
        try:
            transaction_obj = self.get_youpay_transaction_data(
                decrypt_string(pk))
            if transaction_obj:
                payback = B2CPaybackManager()
                response = payback.get_point_program(
                    transaction_obj)
                if response:
                    response_data = self.response_obj.get_success_dict(
                        code=self.response_obj.SUCCESS,
                        success_dict=response
                    )
                    return Response(response_data, status=status.HTTP_200_OK)
                else:
                    message = "Unable to get collect enabled program"
                    data = self.response_obj.get_400_message(message=message)
                    return Response(data.get('errors'),
                                    status=status.HTTP_400_BAD_REQUEST)
            else:
                data = self.response_obj.get_error_dict(
                    error_code=self.response_obj.TRANSACTION_NOT_FOUND)
                return Response(data, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            logger.error("Exception in GetCollectProgramEnabled API for "
                         "transaction ID: {}".format(pk))
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        logger.info(
            "Removing CollectProgramEnabled API called for transaction ID: {}".format(
                pk))
        try:
            transaction_obj = self.get_youpay_transaction_data(
                decrypt_string(pk))
            if transaction_obj:
                payback = B2CPaybackManager()
                response = payback.remove_collect_program_enabled(
                    transaction_obj)
                if response:
                    data = self.response_obj.get_success_dict(
                        code=self.response_obj.SUCCESS,
                        success_dict={}
                    )
                    return Response(data, status=status.HTTP_200_OK)
                else:
                    message = (
                        "Error in removing Collect point enabled "
                        "program {}".format(
                            request.data.get('transaction_id')))
                    logger.error(message)
                    data = self.response_obj.get_400_message(message=message)
                    return Response(data.get('errors'),
                                    status=status.HTTP_400_BAD_REQUEST)
            else:
                data = self.response_obj.get_error_dict(
                    error_code=self.response_obj.TRANSACTION_NOT_FOUND)
                return Response(data, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            logger.error(
                "Exception in removing Collect point enabled program for "
                "transaction ID: {}".format(pk))
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)


class CalculateBalance(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        try:
            transaction_id = request.data.get('transaction_id')
            selected_amount = request.data.get('selected_amount')
            client_code = request.data.get('client_code')
            transaction_obj = self.get_youpay_transaction_data(
                decrypt_string(transaction_id))
            if transaction_obj:
                payload = {
                    'transaction_obj': transaction_obj,
                    "selected_amount": selected_amount,
                    "client_code": client_code
                }

                response_data, code = calculate_balance(payload)

                logger.info("Reward Point(Calculate Balance) API response {}, "
                            "code : {}".format(response_data, code, ))
                if response_data:
                    calculated_item_details = response_data.get(
                        "calculated_item_details", {})
                    processed_calculated_itmes = process_calculated_item_details(
                        calculated_item_details)
                    response_data[
                        "calculated_item_details"] = processed_calculated_itmes

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
                    "CalculateBalance : Transaction not found for {}"
                    "".format(transaction_id))
                return Response(data, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)


class OfferDetails(APIView, YouPayTransactionCRUD):
    """
    API view to fetch and return filtered offer details for a given transaction.

    Methods:
        get(request, pk):
            - Decrypts and retrieves transaction data.
            - Fetches offer details and filters relevant fields.
            - Returns a success response if offers exist.
            - Returns appropriate error responses if transaction or offers are missing.

    Responses:
        - 200 OK: Successfully retrieved and filtered offer details.
        - 400 Bad Request: Unable to fetch offer details or exception occurs.
        - 404 Not Found: Transaction not found.
    """
    response_obj = YouPayResponse()

    def get(self, request, pk):
        try:
            transaction_obj = self.get_youpay_transaction_data(
                decrypt_string(pk))
            if transaction_obj:
                offer_details = self.get_offer_details(transaction_obj)
                if offer_details:
                    filtered_offer_details = {
                        key: [
                            {
                                "brand_code": offer["brand_code"],
                                "brand_name": offer["brand_name"],
                                "brand_logo": offer["brand_logo"],
                                "offer_text": offer["offer_text"],
                                "offer_terms": offer["offer_terms"]
                            }
                            for offer in offers
                        ]
                        for key, offers in offer_details.items()
                    }
                    response_data = self.response_obj.get_success_dict(
                        code=self.response_obj.SUCCESS,
                        success_dict=filtered_offer_details
                    )
                    return Response(response_data, status=status.HTTP_200_OK)
                else:
                    message = "Unable to get offer details"
                    data = self.response_obj.get_400_message(message=message)
                    return Response(data.get('errors'),
                                    status=status.HTTP_400_BAD_REQUEST)


            else:
                data = self.response_obj.get_error_dict(
                    error_code=self.response_obj.TRANSACTION_NOT_FOUND)
                return Response(data, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            logger.error(
                "Exception in getting offer details for transaction ID: {} ".format(
                    pk))
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)
