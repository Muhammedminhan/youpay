import json
import logging
from decimal import Decimal

import requests
from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.constants import PAYBACK_ACTION_EARN, REQUEST_METHOD_POST
from core.exceptions import PaymentConfigurationFailed
from core.messages import PAYMENT_REQUEST_KEYS_ERROR, REDIRECT_URL
from core.response_messages import YouPayResponse
from core.utils import (decrypt_payment_data,
                        encrypt_string, decrypt_string, get_redirect_url,
                        wait_redis_lock, get_gateway_additional_fee,
                        decimal_rounded, encrypt_payment_data,
                        get_cached_payment_method_config,
                        get_config_from_payment_configurations)
from integrations.common import update_offer_details
from integrations.constants import (NEQATY_CLIENT_CODE, QITAF_CLIENT_CODE,
                                    MOKAFAA_CLIENT_CODE,
                                    B2C_REVERSE_REDEMPTION_API,
                                    PAYMENT_REQUEST_B2C_REVERSE_REDEMPTION)
from integrations.v1.gateway_clients.utils import calculate_balance
from payments.constants import (PAYMENT_METHOD_CONFIG_MAPPING,
                                ALLOW_CANCEL_STATUS_LIST,
                                PAYMENT_STATUS_CANCELLED,
                                PAYMENT_STATUS_EXPIRED,
                                PAYMENT_STATUS_PAID, ALLOW_EXPIRE_STATUS_LIST,
                                PAYMENT_METHOD_CITI_REWARDS,
                                PAYMENT_METHOD_QITAF,
                                PAYMENT_METHOD_NEQATY_AND_CARD,
                                PAYMENT_METHOD_NEQATY,
                                PAYMENT_METHOD_MOKAFAA,
                                REDEEM_AMOUNT_APPLICABLE_LIST,
                                PAYMENT_METHOD_MOKAFAA_AND_CARD,
                                PAYMENT_METHOD_ANB,
                                PAYMENT_METHOD_ANB_AND_CARD,
                                PAYMENT_STATUS_REVERSED,
                                REFUND_STATUS_COMPLETED, REFUND_TYPE_POINTS,
                                PAYMENT_STATUS_REFUNDED)
from payments.models import YouPayTransactionData
from services.models import PaymentRequestData
from services.utils import get_payment_redirect_url
from services.v1.auth.client_registration_permission import (
    APIClientRegistrationPermission)
from services.v1.serializers.payment_request import (
    PaymentRequestDataSerializer, PaymentVerifyDataSerializer)
from services.v1.views.common import (YouPayTransactionCRUD, ClientValidator,
                                      AdditionalChargesUpdation)
from services.v1.views.payment_handlers import PaymentHandlers
from services.v1.views.utils import (
    reformat_payment_request_data,
    payment_configuration_check,
    get_country_for_configuration, is_rewards_order_reference
)
from core.common.security.authentication import HMACAuthentication

logger = logging.getLogger(__name__)


class PaymentRequestView(YouPayTransactionCRUD, APIView, ClientValidator,
                         YouPayResponse):
    """
    API endpoint that allows clients create payment request for products.
    """

    def __init__(self):
        self.payment_request_obj = None
        self.return_data = None

    def post(self, request):
        """
        decrypted_data : stores the decrypted data from request

        data_formatted : stores the formatted data from decrypted_data, ie
        data with keys as fields in PaymentRequestData table

        """
        logger.info("session data is {}, keys {}".format(
            request.session, request.session.keys()))

        logger.info("cookie data is {}, keys {}".format(
            request.COOKIES, request.COOKIES.keys()))

        logger.info("Header data is {} ".format(self.request.headers))

        try:
            # Validate client at first
            validate, client = self.validate_client(request)
            if not validate:
                logger.info(
                    "payment request client validation failed for {0}"
                    .format("order_reference"))
                self.return_data = self.get_400_message(
                    message="Client Does Not Exist")
                return Response(self.return_data.get('errors'),
                                status=status.HTTP_400_BAD_REQUEST)
            client_pk = client.pk

            decrypted_data = decrypt_payment_data(request.data,
                                                  client.decrypt_key)
            data_formatted = reformat_payment_request_data(decrypted_data)

            if not data_formatted:
                """
                Decrypted data is empty or does not contain required keys
                """
                message = PAYMENT_REQUEST_KEYS_ERROR
                self.return_data = self.get_400_message(
                    message=message)
                return Response(self.return_data.get('errors'),
                                status=status.HTTP_400_BAD_REQUEST)

            PAYMENT_REDIRECT_URL = get_payment_redirect_url()
            if PAYMENT_REDIRECT_URL is None or PAYMENT_REDIRECT_URL == "":
                """
                Transaction not created, payment url not configured
                """
                self.return_data = self.get_400_message(
                    message="Please configure payment redirect url")

                return Response(self.return_data.get('errors'),
                                status=status.HTTP_400_BAD_REQUEST)

            order_reference = data_formatted.get('order_reference')

            is_offer_applicable = data_formatted.get(
                "order").get("is_offer_applicable")
            logger.info(
                "is_offer_applicable is {} for {}".format(
                    is_offer_applicable,
                    data_formatted.get(
                        "invoice_id")))
            if is_offer_applicable:
                invoice_id = data_formatted.get("invoice_id")
                offer_details = data_formatted.get("order").get(
                    "offer_details")
                update_offer_details(client_pk, invoice_id, offer_details)

            lock_name = ('lock:PaymentRequestView:order_reference_%s'
                         % (order_reference,))
            with wait_redis_lock(lock_name=lock_name):
                data_formatted['api_client'] = client_pk
                serializer = PaymentRequestDataSerializer(data=data_formatted)

                if serializer.is_valid():
                    self.payment_request_obj = serializer.save()
                    transaction_response = self.create_youpay_transaction_data(
                        data_formatted)
                    if transaction_response[
                        'status'] == status.HTTP_201_CREATED:

                        encrypted_transaction_id = encrypt_string(
                            transaction_response['data'][
                                'transaction_id'])

                        language = data_formatted.get('language')

                        redemption_partner = data_formatted.get(
                            'redemption_partner')

                        if redemption_partner:
                            redirect_url = PAYMENT_REDIRECT_URL + "{}/{}/{}".format(
                                language, redemption_partner,
                                encrypted_transaction_id
                            )
                        else:
                            redirect_url = PAYMENT_REDIRECT_URL + "{}/{}".format(
                                language, encrypted_transaction_id)

                        response_data = {
                            "status": status.HTTP_201_CREATED,
                            "message": "created",
                            "url": redirect_url
                        }
                        self.return_data = self.get_success_dict(
                            code=self.SUCCESS,
                            success_dict=response_data
                        )
                        self.save_response_data(self.payment_request_obj,
                                                self.return_data)
                        return Response(self.return_data,
                                        status=status.HTTP_201_CREATED)

                    else:
                        """
                        Transaction not created 
                        """
                        self.return_data = self.get_400_message(
                            message=transaction_response["message"],
                        )
                        logger.error(
                            "Error in creating transaction : {}".format(
                                transaction_response["message"]))

                        self.save_response_data(self.payment_request_obj,
                                                self.return_data)

                        return Response(self.return_data.get('errors'),
                                        status=status.HTTP_400_BAD_REQUEST)
                else:
                    """
                    PaymentRequestDataSerializer validation failed
                    """
                    self.return_data = self.get_error_dict(
                        error_code=self.UNKNOWN_ERR,
                        serializer_error=serializer.errors,
                    )
                    logger.error(
                        "Validation failed for PaymentRequestDataSerializer"
                        " : {}".format(self.return_data))

                    return Response(self.return_data.get('errors'),
                                    status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            import sys, os
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            logger.error("Exception in payment request : {} {} {}"
                         .format(exc_type, fname, exc_tb.tb_lineno))
            logger.error("Exception in payment request : {} "
                         .format(e))
            self.return_data = self.get_400_message(
                message={"error": str(e)},
            )

            if self.payment_request_obj is not None:
                '''Save response data to PaymentRequestData table'''
                self.save_response_data(self.payment_request_obj,
                                        self.return_data)

            logger.error("Error in creating payment request : {}".format(e))
            return Response(self.return_data,
                            status=status.HTTP_400_BAD_REQUEST)
        finally:
            logger.info(
                "Payment request completed : {}".format(self.return_data))

    def save_response_data(self, payment_request_obj, response_data):
        """
        Save response data to PaymentRequestData table
        """
        try:
            PaymentRequestData.objects.filter(
                id=payment_request_obj.id).update(response_data=response_data)
        except Exception as e:
            logger.error("Error in saving response data for : {}".format(e))

    def verify_transaction(self, data, **kwargs):
        try:

            payment_method = kwargs.get("payment_method")

            serializer = PaymentVerifyDataSerializer(data=data)
            if serializer.is_valid():
                """Validate transaction data with youpay client"""
                transaction_id = serializer.validated_data.get(
                    'transaction_id')
                transaction_obj = self.get_youpay_transaction_data(
                    transaction_id)

                if transaction_obj.api_client is None:
                    """Client does not exist"""
                    return_data = self.get_400_message(
                        message="API Client Does Not Exist or Inactive")
                    return return_data, status.HTTP_400_BAD_REQUEST

                if transaction_obj.api_client.is_active is False:
                    '''Skip verification if client is inactive'''
                    dummy_response = {
                        "is_verified": True,
                    }
                    logger.info(
                        "Client is inactive, skipping payment verification with "
                        "API Client for : {}".format(transaction_id))
                    return dummy_response, status.HTTP_200_OK

                client_verify_url = transaction_obj.verify_url
                if client_verify_url is None or client_verify_url == "":
                    return_data = self.get_400_message(
                        message="Please configure client verify url")
                    return return_data, status.HTTP_400_BAD_REQUEST
                else:
                    """
                    Verify transaction with client by calling verify url
                    """

                    verify_headers = {
                        'Accept': 'application/json',
                        "API-KEY": transaction_obj.api_client.api_key,
                        "API-SECRET": transaction_obj.api_client.api_secret,
                    }

                    verify_body = self.prepare_client_verify_data(
                        payment_method, transaction_obj)

                    logger.info("Client verification request data {} ".format(
                        verify_body))
                    response = self.verify_transaction_with_client(
                        url=client_verify_url, body=json.dumps(verify_body),
                        headers=verify_headers)
                    logger.info(
                        "Client verifying on {}, request send data : {}"
                        " response data{} for transaction {}".format(
                            client_verify_url, verify_body, response.text,
                            transaction_obj.transaction_id))

                    if response:
                        return_data = self.get_success_dict(
                            code=self.SUCCESS,
                            success_dict=response.json()
                        )
                        return return_data, status.HTTP_200_OK
                    else:
                        logger.info(
                            "Client verify url {} not "
                            "responding".format(client_verify_url))
                        redirect_url = get_redirect_url(
                            transaction_obj.cancel_url, transaction_id)

                        # Preparing response data as per the payment API response
                        data = {
                            "is_redirect": True,
                            "is_success": False,
                            "redirect_url": redirect_url,
                            "message": self.MESSAGE.get(
                                self.CLIENT_TRANSACTION_VERIFICATION_FAILED),
                            "code": self.CLIENT_TRANSACTION_VERIFICATION_FAILED,
                        }
                        return data, status.HTTP_400_BAD_REQUEST

            else:
                response_data = self.get_error_dict(
                    error_code=self.UNKNOWN_ERR,
                    serializer_error=serializer.errors,
                )
                return response_data.get(
                    'errors'), status.HTTP_400_BAD_REQUEST
        except Exception as e:
            logger.error(
                "Excepction occured during client verification {}".format(
                    str(e)))
            return {}, status.HTTP_400_BAD_REQUEST

    def prepare_client_verify_data(self, payment_method, transaction_obj):
        """
        For payment methods citi/Qitaf there is no service charge and extra
        charges so base amount is to be verified instead of amount
        """

        amount = transaction_obj.amount
        if payment_method in [PAYMENT_METHOD_CITI_REWARDS,
                              PAYMENT_METHOD_QITAF, PAYMENT_METHOD_MOKAFAA,
                              PAYMENT_METHOD_ANB]:
            amount = transaction_obj.base_amount
        elif payment_method in [PAYMENT_METHOD_NEQATY_AND_CARD,
                                PAYMENT_METHOD_NEQATY,
                                PAYMENT_METHOD_MOKAFAA_AND_CARD,
                                PAYMENT_METHOD_ANB_AND_CARD]:
            amount = transaction_obj.brand_calculations.get(
                'sum_net_amount', None)

        verify_body = {
            "transaction_id": str(transaction_obj.transaction_id),
            "invoice_id": transaction_obj.invoice_id,
            "amount": str(amount),
            "currency": transaction_obj.currency,
            "payment_method": payment_method,
        }
        if is_rewards_order_reference(transaction_obj.order_reference):
            verify_body["order_reference"] = str(
                transaction_obj.order_reference)
        return verify_body

    def get_api_client_keys(self, transaction_obj):
        api_key = ""
        api_secret = ""
        if transaction_obj and transaction_obj.api_client is not None:
            api_key = transaction_obj.api_client.api_key
            api_secret = transaction_obj.api_client.api_secret
        return api_key, api_secret

    def verify_transaction_with_client(self, **kwargs):
        url = kwargs.get('url')
        body = kwargs.get('body')
        headers = kwargs.get('headers')
        response = requests.post(url, json=body, headers=headers)
        logger.info("Verify client with data {} ,Response {}".format(
            body, response.text))
        return response

    def prepair_frontend_redirect_url(self, transaction_obj):
        """Prepare frontend redirect url"""
        redirect_url = get_redirect_url(
            transaction_obj.redirect_url, transaction_obj.transaction_id)
        return redirect_url


class TestPaymentRequestView(YouPayTransactionCRUD, APIView, ClientValidator):
    """
    Test API endpoint for encrypting request data
    """
    permission_classes = [APIClientRegistrationPermission]

    def post(self, request):
        data = self.request.data
        enc_data = eval(encrypt_payment_data(data))
        return Response({
            "response": enc_data,
        })


class PaymentCancelledView(YouPayTransactionCRUD, APIView, ClientValidator):
    response_obj = YouPayResponse()

    def post(self, request):
        try:
            logger.info("Triggered PaymentCancelledView")
            redirect_url = None
            data = self.request.data
            encrypted_transaction_id = data.get('transaction_id')
            if not encrypted_transaction_id:
                data = self.response_obj.get_error_dict(
                    error_code= self.response_obj.VALIDATION_FAILED)
                return Response(data,
                                status=status.HTTP_400_BAD_REQUEST)

            transaction_id = decrypt_string(encrypted_transaction_id)
            transaction_object = self.get_youpay_transaction_data(
                transaction_id)
            if transaction_object:
                if transaction_object.payment_status in ALLOW_CANCEL_STATUS_LIST:
                    self.update_youpay_transaction_data({
                        'transaction_id': transaction_id,
                        'payment_status': PAYMENT_STATUS_CANCELLED
                    })

                    redirect_url = get_redirect_url(transaction_object.cancel_url,
                                                    transaction_id)
                    logger.info(
                        "Payment cancelled for transaction_id : {}, "
                        "order reference : {}".format(
                            transaction_id, transaction_object.order_reference))

                elif transaction_object.payment_status == PAYMENT_STATUS_PAID:
                    redirect_url = get_redirect_url(
                        transaction_object.success_url,
                        transaction_id)
                else:
                    redirect_url = get_redirect_url(
                        transaction_object.failure_url,
                        transaction_id)
                return Response({
                    'is_redirect': True,
                    REDIRECT_URL: redirect_url
                })
            else:
                data = self.response_obj.get_error_dict(
                    error_code=self.response_obj.VALIDATION_FAILED)
                return Response(data,
                                status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error("Error in payment cancel api  : {}".format(e))
            return Response({
                "error": str(e),
            })


class TransactionExpireView(YouPayTransactionCRUD, APIView, ClientValidator,
                            YouPayResponse):

    def __init__(self):
        self.return_data = None

    def post(self, request):
        try:
            logger.info("Triggered TransactionExpireView")

            data = self.request.data
            transaction_id = decrypt_string(data.get('transaction_id'))
            transaction_object = self.get_youpay_transaction_data(
                transaction_id)

            if transaction_object.payment_status in ALLOW_EXPIRE_STATUS_LIST:
                self.update_youpay_transaction_data({
                    'transaction_id': transaction_object.transaction_id,
                    'payment_status': PAYMENT_STATUS_EXPIRED
                })

            logger.info(
                "Payment status set to expired for transaction_id "
                ": {}".format(transaction_id))
            redirect_url = (transaction_object.cancel_url +
                            '?transaction_id=' + transaction_id)
            response_data = {"status": status.HTTP_200_OK,
                             "is_redirect": True,
                             REDIRECT_URL: redirect_url,
                             "message": "Successfully expired transaction"}

            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("Error in transaction expire api ", exc_info=e)
            return Response({"error": str(e), })


class AdditionalChargeCalculation(APIView, AdditionalChargesUpdation,
                                  YouPayTransactionCRUD):
    response_obj = YouPayResponse()
    transaction = None
    payment_option = None
    additional_charges = {}

    def get_400_message(self):
        """
        400 error handling method
        """
        message = ('Request data is not in proper format. '
                   'Required data is missing or incorrect.')
        return_data = self.response_obj.get_400_message(
            message=message)
        return return_data

    def calculate_processing_fee(self, additional_fee, base_amount,
                                 vat_percent):
        """
        Calulate proccessing fee and vat percentage for processing fee
        """
        processing_fee = 0
        percentage = additional_fee.percentage
        fixed_amount = additional_fee.fixed_amount
        if percentage:
            processing_fee += (base_amount * (percentage / 100))
        if fixed_amount:
            processing_fee += fixed_amount
        processing_fee_vat = vat_percent * processing_fee
        return processing_fee, processing_fee_vat

    def calculate_additional_charges(self, additional_fee):
        """
        method to calculate new vat amount
        based on the additional charges for paypal
        """
        try:
            order_amount = self.transaction.base_amount
            service_fee = self.transaction.service_fee
            decimal_notation = (
                self.transaction.additional_currency_decimal_notation)
            vat_percent = (self.transaction.additional_vat_percentage / 100)
            processing_fee, processing_fee_vat = (
                self.calculate_processing_fee(
                    additional_fee, order_amount, vat_percent
                ))
            processing_fee = decimal_rounded(processing_fee, decimal_notation)
            processing_fee_vat = decimal_rounded(processing_fee_vat,
                                                 decimal_notation)
            vat_amount = vat_percent * (service_fee + processing_fee)
            vat_amount = decimal_rounded(vat_amount, decimal_notation)
            total_amount = (order_amount + service_fee +
                            processing_fee + vat_amount)
            total_amount = decimal_rounded(total_amount, decimal_notation)

            self.additional_charges = {
                "processing_fee": processing_fee,
                "processing_fee_vat": processing_fee_vat,
                "new_vat": vat_amount,
                "total_amount": total_amount
            }

            """ Saving to additional charges table"""
            dct_update_data = {
                "transaction": self.transaction,
                "payment_option": self.payment_option
            }
            dct_update_data.update(self.additional_charges)
            self.create_additional_charges(dct_update_data)
        except Exception as e:
            logger.error("Exception occurred during payment gateway "
                         "processing fee calculation of {} {}"
                         "".format(self.transaction.transaction_id, str(e)))
            raise e

    def get(self, request, *args, **kwargs):
        """
        Calculates processing fees based on the
        additional charges configured for each payment options.
        """
        try:
            query_params = request.query_params
            logger.info("Additional charge calculating api "
                        "is executing {}".format(query_params))
            transaction_id = decrypt_string(query_params.get('id'))
            self.payment_option = query_params.get('payment_option')
            if (not query_params or
                    any([not transaction_id, not self.payment_option])):
                return_data = self.get_400_message()
                return Response(return_data.get('errors'),
                                status=status.HTTP_400_BAD_REQUEST)

            additional_fee = get_gateway_additional_fee(self.payment_option)
            if additional_fee:
                self.transaction = (
                    self.get_youpay_transaction_data(transaction_id))
                additional_charge_obj = self.get_additional_charges(
                    transaction_id, self.payment_option)
                if not additional_charge_obj:
                    self.calculate_additional_charges(additional_fee)
                else:
                    self.additional_charges = {
                        "processing_fee": (
                            additional_charge_obj.additional_processing_fee),
                        "processing_fee_vat": (
                            additional_charge_obj.additional_processing_fee_vat),
                        "new_vat": (
                            additional_charge_obj.additional_vat),
                        "total_amount": (
                            additional_charge_obj.additional_total_amount)
                    }

                additional_charge_update = {
                    "order_amount": self.transaction.base_amount,
                    "service_fee": self.transaction.service_fee
                }
                self.additional_charges.update(additional_charge_update)

                data = self.response_obj.get_success_dict(
                    code=1000,
                    success_dict=(
                        {"additional_charges": self.additional_charges})
                )
                return Response(data,
                                status=status.HTTP_200_OK)
            else:
                data = self.response_obj.get_success_dict(
                    code=1000,
                    success_dict={"additional_charges": {}}
                )
                return Response(data,
                                status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("Error in fetching additional charges :"
                         "{}".format(str(e)))
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)


class EarnRedemptionPartnerPoints(YouPayTransactionCRUD, APIView,
                                  ClientValidator,
                                  YouPayResponse):

    def __init__(self, ):
        self.class_name = "{}:".format("EarnRedemptionPartnerPoints")


    def get_redeemed_amount(self, transaction_obj):

        redeemed_amount = (transaction_obj.redeemed_amount if
                transaction_obj.redeemed_amount else 0.0)

        if transaction_obj.payment_method not in REDEEM_AMOUNT_APPLICABLE_LIST:
            """
            This case happens if customer switches payment method just before
            payment through b2c payback, this will let to reset the 
            brand calculations with selected amount 0
            """
            redeemed_amount = 0.0

        logger.info(
            "{} get_redeemed_amount, payment method{} for {} is {}".format(
                self.class_name,
                transaction_obj.payment_method,
                transaction_obj.transaction_id,
                redeemed_amount
            ))

        return str(redeemed_amount)

    def get_earn_points(self, **kwargs):
        '''
        This method is used to get earn points by identifying the redemption
        partner
        '''
        transaction_id = kwargs.get('transaction_id', None)
        transaction_obj = kwargs.get('transaction_obj', None)
        mobile_number = None
        is_success = False
        collect_enabled = False
        earned_points = None
        earn_reference = None
        partner_response = None
        partner_response_code = None
        code = None
        calculated_item_details = None
        program_name = transaction_obj.point_program
        logger.info("{} working for {}, for transaction {}".format(
            self.class_name, program_name, transaction_id
        ))

        payment_configuration_check(transaction_obj=transaction_obj,
                                    payment_method=program_name,
                                    payback_action=PAYBACK_ACTION_EARN)
        self.call_brand_calculation(transaction_obj, program_name)

        if program_name == PAYMENT_METHOD_NEQATY:
            collect_enabled = transaction_obj.point_collection_enabled
            mobile_number = transaction_obj.points_collected_mobile_number

            from integrations.v1.gateway_clients.neqaty_service import (
                NeqatyServiceManager)
            neqaty_obj = NeqatyServiceManager()
            response, code = neqaty_obj.collect_points(transaction_obj)
            partner_response = response
            partner_response_code = code
            if code == self.SUCCESS:
                earn_reference = response.get("partner_response").get(
                    "earn_reference")
                calculated_item_details = response.get(
                    "partner_response", {}).get("calculated_item_details")
                is_success = True
            message = "Pont Collect requested for: {}".format(
                PAYMENT_METHOD_NEQATY)

        elif program_name == PAYMENT_METHOD_QITAF:
            collect_enabled = transaction_obj.is_qitaf_enabled
            mobile_number = transaction_obj.qitaf_phone_number

            from services.v1.api_clients.qitaf_service import (
                QitafCollectPointsAPIView)
            qitaf_view_obj = QitafCollectPointsAPIView()
            response, code, earned_points = qitaf_view_obj.collect_reward_point(
                transaction_obj)
            partner_response = response
            partner_response_code = code

            if code == self.SUCCESS:
                partner_response_status = response.get("status", False)
                is_success = partner_response_status
                earned_points = response.get("partner_response").get(
                    "reward_point")
                earn_reference = response.get("partner_response").get(
                    "earn_reference")
                calculated_item_details = response.get(
                    "partner_response", {}).get("calculated_item_details")

            message = "Pont Collect requested for {}".format(
                PAYMENT_METHOD_QITAF)

        elif program_name == PAYMENT_METHOD_MOKAFAA:
            collect_enabled = transaction_obj.point_collection_enabled
            mobile_number = transaction_obj.points_collected_mobile_number

            from integrations.v1.gateway_clients.mokafa_service import (
                MokafaServiceManager)
            mokafa_obj = MokafaServiceManager()
            response, code = mokafa_obj.collect_points(transaction_obj)
            partner_response = response
            partner_response_code = code
            if code == self.SUCCESS:
                earn_reference = response.get("partner_response").get(
                    "earn_reference")
                earned_points = response.get("partner_response").get(
                    "earned_points")
                calculated_item_details = response.get(
                    "partner_response", {}).get("calculated_item_details")
                is_success = True
            message = "Pont Collect requested for {}".format(
                PAYMENT_METHOD_MOKAFAA)

        else:
            message = "Unknown redemption partner {}".format(
                transaction_obj.point_program)
            response = None

        logger.info("{} {} API response received {}".format(
            self.class_name, program_name,
            response
        ))

        if code == self.SUCCESS:
            transaction_obj.earn_reference = earn_reference
            transaction_obj.earned_point = earned_points
            transaction_obj.save()

            logger.info(
                "{} collection success for program {}, tid :{}".format(
                    self.class_name, program_name, transaction_id
                ))
        else:
            reset = False
            reset_calculated_item_details = response.get(
                "partner_response", {}).get("partner_response", {}).get(
                "calculated_item_details") if response else None
            if reset_calculated_item_details:
                transaction_obj.brand_calculations = reset_calculated_item_details
                reset = True
                transaction_obj.save()

            logger.info(
                "{} collection failed for program {}, tid :{}, rest status : "
                "{}, reset data {}".format(
                    self.class_name, program_name, transaction_id,
                    reset, reset_calculated_item_details
                ))
        message = "{} status {} for {}".format(message, is_success,
                                               transaction_id)

        logger.info(
            "{} Partner response code is {}, response : {} for transaction:"
            " {}".format(self.class_name, partner_response_code,
                         partner_response, transaction_id))

        return {
            "status": is_success,
            "message": message,
            "mobile_number": mobile_number,
            "earned_points": earned_points,
            "program_name": program_name,
            "collect_enabled": collect_enabled
        }

    def call_brand_calculation(self, transaction_obj, program_name):
        """
        Update brand calculations
        """
        client_code = self.get_client_code(program_name)

        payload = {
            'transaction_obj': transaction_obj,
            "selected_amount": self.get_redeemed_amount(transaction_obj),
            "client_code": client_code,
            "payback_action": PAYBACK_ACTION_EARN
        }

        response_data, code = calculate_balance(payload)

        if code == self.SUCCESS:
            calculated_items = response_data.get('calculated_item_details',
                                                 {}).get(
                'calculated_item_details', [])
            existing_data = transaction_obj.brand_calculations or {}
            existing_items = existing_data.get('calculated_item_details', [])

            existing_items_map = {item.get('item_id'): item for item in
                                  existing_items}

            for item in calculated_items:
                item_id = item.get('item_id')
                if item_id in existing_items_map:
                    existing_items_map[item_id]['earn_discount'] = item.get(
                        'earn_discount')
            existing_data['calculated_item_details'] = list(
                existing_items_map.values())

            transaction_obj.brand_calculations = existing_data

        logger.info("{} Brand Calculated for transaction {}".format(
            self.class_name, transaction_obj.transaction_id))

    def get_client_code(self, program_name):
        if program_name == PAYMENT_METHOD_NEQATY:
            client_code = NEQATY_CLIENT_CODE
        elif program_name == PAYMENT_METHOD_MOKAFAA:
            client_code = MOKAFAA_CLIENT_CODE
        else:
            client_code = QITAF_CLIENT_CODE
        return client_code

    def validate_earn_enabled(self, transaction_obj):
        """
        Function to check whether earn is enabled or not
        """

        country = get_country_for_configuration(transaction_obj)
        if not country:
            logger.error(
                "{} Unregistered Country ({}) received for transaction {}"
                "".format(self.class_name, transaction_obj.country_code,
                          transaction_obj.transaction_id)
            )
            raise PaymentConfigurationFailed(
                "Country not registered for transaction {}".format(
                    transaction_obj.transaction_id))

        payment_method = (
            transaction_obj.point_program if transaction_obj.point_program
            else transaction_obj.payment_method)

        query_obj = {
            'payment_method__active': True,
            'client__id': transaction_obj.api_client.id,
            'country__iso_code': transaction_obj.country_code,
            'payment_method__payment_method': (
                PAYMENT_METHOD_CONFIG_MAPPING.get(payment_method)),
            'active': True
        }

        if transaction_obj.is_guest:
            query_obj['guest_user_enabled'] = True

        logger.info("{} Query filter ".format(query_obj))

        payment_method_query = Q(**query_obj)
        payment_method_config_qs = get_cached_payment_method_config()
        payment_method_configs = payment_method_config_qs.filter(
            payment_method_query)

        if not payment_method_configs.exists():
            msg = (
                "{} No Active Payment Configuration for transaction-{}, "
                "client-({}), country-({}), guest user status-({}), point "
                "program | payment method-({}|{}), is_full_redemption-({})"
                "".format(
                    self.class_name,
                    transaction_obj.transaction_id,
                    transaction_obj.api_client,
                    transaction_obj.country_code,
                    transaction_obj.is_guest,
                    transaction_obj.point_program,
                    transaction_obj.payment_method,
                    transaction_obj.is_full_redemption
                ))

            logger.error(msg)

            raise PaymentConfigurationFailed(
                "No Active Payment Configuration for transaction-{}, "
                "client-({}), country-({}), guest user status-({}), payment "
                "method-({}), is_full_redemption-({})".format(
                    transaction_obj.transaction_id,
                    transaction_obj.api_client,
                    transaction_obj.country_code,
                    transaction_obj.is_guest,
                    transaction_obj.payment_method,
                    transaction_obj.is_full_redemption
                )
            )

        payment_method_config = payment_method_configs.first()
        earn_enabled = payment_method_config.payment_method.earn_enabled
        earn_msg = "{} Earn is disabled in youpay for transaction {}".format(
            self.class_name, transaction_obj.transaction_id
        )

        if transaction_obj.is_full_redemption == False:
            """
            Case to check whether transaction is earn, and partial
            """
            earn_enabled = payment_method_config.payment_method.earn_on_partial_redemption
            earn_msg = ("{} Partial Earn is disabled in youpay for "
                        "transaction {}").format(
                self.class_name, transaction_obj.transaction_id)
        if not earn_enabled:
            logger.error(earn_msg)
            raise PaymentConfigurationFailed(earn_msg)

        return earn_enabled
    
    def post(self, request):
        try:
            transaction_id = None

            validate, client = self.validate_client(request)
            if not validate:
                logger.info(
                    "{} payment request client validation failed"
                    .format(self.class_name))
                return_data = self.get_400_message(
                    message="Client Does Not Exist")
                return Response(return_data.get('errors'),
                                status=status.HTTP_400_BAD_REQUEST)
            data = self.request.data
            transaction_id = decrypt_string(data.get('transaction_id'))
            transaction_object = self.get_youpay_transaction_data(
                transaction_id)

            if transaction_object:
                # call redemption partner earn flow
                logger.info("{} started for transaction_id: {}".format(
                    self.class_name, transaction_id))

                self.validate_earn_enabled(transaction_object)

                earn_response = self.get_earn_points(
                    transaction_id=transaction_id,
                    transaction_obj=transaction_object)

                logger.info("{} worked for transaction : {}, response : {}"
                            "".format(self.class_name, transaction_id,
                                      earn_response))

                response_data = {
                    "status": earn_response.get("status"),
                    "message": earn_response.get("message"),
                }

                return Response(response_data, status=status.HTTP_200_OK)
            else:
                response_data = {
                    "status": False,
                    "message": "Transaction({}) not found".format(
                        transaction_id),
                }
                return Response(response_data,
                                status=status.HTTP_400_BAD_REQUEST)

        except PaymentConfigurationFailed as e:
            response_data = {
                "status": False,
                "message": str(e),
            }
            logger.error(
                "{} PaymentConfigurationFailed Validation failed for {}"
                "".format(self.class_name, transaction_id))
            return Response(response_data,
                            status=status.HTTP_200_OK)

        except Exception as e:
            logger.error("{} Error in Earn Redemption Partner Points api "
                         "".format(self.class_name), exc_info=e)
            return Response({"error": str(e), })


class RefundPointsAPIView(APIView, ClientValidator, YouPayResponse,
                          PaymentHandlers):
    """
    API to refund redeemed points
    """
    authentication_classes = [HMACAuthentication]

    def __init__(self):
        self.validate, self.client = None, None

    def hmac_secret(self, request):
        self.validate, self.client = self.validate_client(request)
        return self.client.api_secret

    def post(self, request):
        try:
            if not self.validate:
                logger.info("Refund request client validation failed")
                self.return_data = self.get_400_message(
                    message="Client Does Not Exist"
                )
                return Response(
                    self.return_data.get("errors"),
                    status=status.HTTP_400_BAD_REQUEST
                )

            order_id = request.data.get("order_id")
            refund_amount = request.data.get("refund_amount")
            currency = request.data.get("currency")
            transaction_id = request.data.get("transaction_id")
            refund_reason = request.data.get("refund_reason")

            missing_fields = [
                field for field, value in {
                    "order_id": order_id,
                    "transaction_id": transaction_id,
                    "refund_amount": refund_amount,
                    "currency": currency,
                    "refund_reason": refund_reason,
                }.items()
                if value in (None, "")
            ]

            if missing_fields:
                self.return_data = self.get_400_message(
                    message=f"Missing required fields: {', '.join(missing_fields)}"
                )
                return Response(
                    self.return_data.get("errors"),
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                transaction = YouPayTransactionData.objects.get(
                    invoice_id=order_id,
                    api_client=self.client,
                    payment_status=PAYMENT_STATUS_PAID,
                    currency=currency,
                    amount=Decimal(refund_amount),
                    transaction_id=transaction_id
                )
            except YouPayTransactionData.DoesNotExist:
                logger.info(
                    "Refund transaction not found | invoice_id=%s | transaction_id=%s",
                    order_id, transaction_id
                )
                self.return_data = self.get_error_dict(
                    self.PAYMENT_REFUND_NOT_ELIGIBLE
                )
                return Response(
                    self.return_data.get("errors"),
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not transaction.redeemed_points or transaction.redeemed_points <= 0:
                logger.info(
                    "No redeemed points found | transaction_id=%s",
                    transaction.transaction_id
                )
                self.return_data = self.get_error_dict(
                    self.PAYMENT_REFUND_NOT_ELIGIBLE
                )
                return Response(
                    self.return_data.get("errors"),
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                payment_method = transaction.payment_method.split("_")[0]
                b2c_gateway_obj = get_config_from_payment_configurations(
                    transaction, payment_method
                )

                url = b2c_gateway_obj.domain + B2C_REVERSE_REDEMPTION_API
                payload = {
                    "reference_id": transaction.payment_reference
                }
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': b2c_gateway_obj.api_key,
                    'X-API-KEY': b2c_gateway_obj.api_key
                }

                response = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=10
                )

                request_data_log = payload.copy()
                request_data_log.update({"refund_request_data": request.data})
                self.create_youpay_to_payment_gateways_data(
                    transaction_obj=transaction,
                    transaction_id=transaction.transaction_id,
                    request_data=json.dumps(request_data_log),
                    response_data=response.text,
                    request_method=REQUEST_METHOD_POST,
                    request_type=PAYMENT_REQUEST_B2C_REVERSE_REDEMPTION
                )

                if response.status_code != 200:
                    logger.error(
                        "Redemption reversal failed | transaction_id=%s | "
                        "status=%s | response=%s",
                        transaction.transaction_id,
                        response.status_code,
                        response.text
                    )
                    self.return_data = self.get_error_dict(
                        self.PAYMENT_REFUND_FAILED
                    )
                    return Response(
                        self.return_data.get("errors"),
                        status=status.HTTP_400_BAD_REQUEST
                    )

                logger.info(
                    "Redemption reversal success | transaction_id=%s",
                    transaction.transaction_id
                )

            except Exception as e:
                logger.error(
                    "Error during redemption reversal | transaction_id=%s | "
                    "error=%s", transaction.transaction_id, str(e)
                )
                self.return_data = self.get_400_message(
                    message="Unable to process points refund at the moment"
                )
                return Response(
                    self.return_data.get("errors"),
                    status=status.HTTP_400_BAD_REQUEST
                )

            payable_amount = transaction.payable_amount
            transaction.payment_status = (
                PAYMENT_STATUS_REVERSED
                if payable_amount > 0
                else PAYMENT_STATUS_REFUNDED
            )
            transaction.refund_reason = refund_reason
            transaction.save(update_fields=["payment_status", "refund_reason"])

            success_response = {
                "order_id": order_id,
                "amount": refund_amount,
                "refund_type": REFUND_TYPE_POINTS,
                "refund_status": REFUND_STATUS_COMPLETED,
                "message": "Redeemed points refunded successfully"
            }

            self.return_data = self.get_success_dict(
                code=self.SUCCESS,
                success_dict=success_response
            )

            return Response(self.return_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(
                "Unhandled error in RefundPointsAPIView | error=%s",
                str(e)
            )
            self.return_data = self.get_400_message(
                message="Something went wrong while processing refund"
            )
            return Response(
                self.return_data.get("errors"),
                status=status.HTTP_400_BAD_REQUEST
            )
