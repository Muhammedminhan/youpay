import logging
from decimal import Decimal

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.core.exceptions import ObjectDoesNotExist

from core.response_messages import YouPayResponse
from core.utils import decrypt_string
from services.models import APIClient
from services.v1.views.common import (YouPayTransactionCRUD,
                                      get_processing_charge,
                                      AdditionalChargesUpdation)
from payments.serializers.youpay_payments import (
    YouPayTransactionDataSerializer)
from gateways.paypal.integrations import PaypalManager
from core.messages import TRANSACTION_DOESNT_EXIST
from integrations.constants import ADDITIONAL_PROCESSING_FEE, PAYPAL_HUB_CODE
from payments.constants import PAYMENT_METHOD_PAYPAL

logger = logging.getLogger(__name__)


class PayPalChargeAPIView(APIView, YouPayTransactionCRUD,
                          AdditionalChargesUpdation):
    """
    API for PayPal charge calculation
    """
    response_obj = YouPayResponse()
    vat_charge_percentage = 0

    def calculate_paypal_charge(self, transaction):
        """
        Calculate PayPal processing fee and new additional VAT.
        """
        currency = transaction.currency
        base_amount = Decimal(transaction.base_amount)
        cart_base_amount = Decimal(transaction.cart_base_amount)
        charge_type = ADDITIONAL_PROCESSING_FEE
        payment_gateway = PAYPAL_HUB_CODE
        payment_method = PAYMENT_METHOD_PAYPAL

        processing_fee_charge, vat_charge = get_processing_charge(
            currency, charge_type, payment_gateway, payment_method)

        if processing_fee_charge is not None and vat_charge is not None:
            processing_fee_decimal = processing_fee_charge/100
            vat_decimal = vat_charge/100
            self.vat_charge_percentage = vat_decimal

            processing_fee = base_amount * processing_fee_decimal
            cart_processing_fee = cart_base_amount * processing_fee_decimal
            new_vat_amount = (transaction.VAT_amount +
                              (processing_fee * vat_decimal))
            new_cart_vat_amount = (transaction.cart_VAT_amount +
                                   (cart_processing_fee * vat_decimal))
            new_amount = (base_amount + transaction.service_fee +
                          processing_fee + new_vat_amount)
            new_cart_amount = (cart_base_amount + transaction.cart_service_fee
                                + cart_processing_fee + new_cart_vat_amount)

            response_data = {
                "amount": new_amount,
                "currency": currency,
                "base_amount": base_amount,
                "service_fee": transaction.service_fee,
                "vat_amount": new_vat_amount,
                "processing_fee": processing_fee,
                "cart_amount": new_cart_amount,
                "cart_currency": transaction.cart_currency,
                "cart_base_amount": transaction.cart_base_amount,
                "cart_service_fee": transaction.cart_service_fee,
                "cart_vat_amount": new_cart_vat_amount,
                "cart_processing_fee": cart_processing_fee,
            }
            return response_data
        return None

    def update_additional_charge_table(self, data):
        """
        Update additional charge table
        """
        try:
            update_data = {
                'transaction': data.get('transaction'),
                'payment_option': PAYMENT_METHOD_PAYPAL,
                'new_vat': data.get('vat_amount'),
                'processing_fee': data.get('processing_fee'),
                'processing_fee_vat': (data.get('processing_fee') *
                                       self.vat_charge_percentage),
                'total_amount': data.get('amount')
            }
            self.create_additional_charges(update_data)
        except Exception as e:
            logger.error(f"Failed to update additional charge table: {str(e)}")

    def get(self, request):
        """
        Calculates PayPal additional charges and VAT based on currency
        """
        try:
            transaction_id = request.query_params.get("id")
            logger.info(f"Received PayPal charge calculation request for "
                        f"Transaction ID: {transaction_id}")

            decrypted_id = decrypt_string(transaction_id)
            transaction_obj = self.get_youpay_transaction_data(decrypted_id)

            response_data = self.calculate_paypal_charge(transaction_obj)

            if response_data:
                api_client_obj = APIClient.objects.get(
                    name=transaction_obj.api_client)
                allow_aed_converted_amount = (
                    api_client_obj.allow_aed_converted_amount)
                response_data.update({
                    "allow_aed_converted_amount": allow_aed_converted_amount,
                    "transaction": transaction_obj
                })
                self.update_additional_charge_table(response_data)
                response_data.pop("transaction")
                data = self.response_obj.get_success_dict(
                    code=self.response_obj.SUCCESS,
                    success_dict=response_data
                )
                return Response(data, status=status.HTTP_200_OK)
            else:
                data = self.response_obj.get_error_dict(
                    error_code=self.response_obj.CHARGE_CALCULATION_FAILED)
                return Response(data, status=status.HTTP_400_BAD_REQUEST)

        except ObjectDoesNotExist as e:
            data = self.response_obj.get_404_message(message=str(e))
            return Response(data, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)


class PayPalPaymentAPIView(APIView, YouPayTransactionCRUD):
    """
    API view for creating a PayPal order.
    Handles the request from frontend, invokes PayPal integration,
    and returns the API response.
    """
    response_obj = YouPayResponse()

    def post(self, request):
        """
        Handles PayPal order creation.
        """
        try:
            transaction_id = request.data.get("transaction_id")
            logger.info(f"Received PayPal order creation request for "
                        f"Transaction ID: {transaction_id}")

            decrypted_id = decrypt_string(transaction_id)
            transaction_obj = self.get_youpay_transaction_data(decrypted_id)

            if transaction_obj:
                serializer = YouPayTransactionDataSerializer(transaction_obj)
                transaction_data = serializer.data

                transaction_data.update({
                    'transaction_obj': transaction_obj,
                    'amount': float(transaction_data['amount'])
                })

                paypal = PaypalManager()
                response_data, code = paypal.create_order(transaction_data)

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
                    message=TRANSACTION_DOESNT_EXIST)
                return Response(data, status=status.HTTP_400_BAD_REQUEST)
        except ObjectDoesNotExist as e:
            data = self.response_obj.get_404_message(message=str(e))
            return Response(data, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Exception occurred while creating PayPal "
                         f"order: {str(e)}", exc_info=True)
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)
