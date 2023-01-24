import json
import logging

from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from b2cpaybackclient.models import PurchaseRequest
from b2cpaybackclient.libs.authentication import SignatureAuthentication
from b2cpaybackclient.utils import get_decimal
from b2cpaybackclient.v1.serializers.purchaserequest_serializer import (
    PurchaseRequestSerializer)


logger = logging.getLogger(__name__)


def get_purchase_request_object(reference):
    with transaction.atomic():
        purchase_obj = None
        if reference:
            try:
                purchase_obj = (
                    PurchaseRequest.objects.select_for_update().get(
                       reference_id=reference))
            except PurchaseRequest.DoesNotExist:
                purchase_obj = None
        return purchase_obj


class WebhookListener(APIView):
    authentication_classes = (SignatureAuthentication, )

    def post(self, request):
        request_data = json.loads(request.data)
        try:
            invoice = str(request_data.get('invoice', None))
            logger.info("B2cpayback webhook received for invoice {}".format(
                invoice))

            reference = request_data.get('reference_id', None)
            purchase_obj = get_purchase_request_object(reference)
            if purchase_obj:
                logger.info(
                    "B2cpayback webhook listener updating data for invoice "
                    "{0}".format(invoice))
                serializer = PurchaseRequestSerializer(
                    purchase_obj, data=request_data, partial=True)
            else:
                serializer = PurchaseRequestSerializer(
                    data=request_data, partial=True)

            if serializer.is_valid(raise_exception=True):
                serializer.save()
            #     purchase_obj.payment_status = request_data.get(
            #         'payment_status', False)
            #     purchase_obj.redemption_status = request_data.get(
            #         'redemption_status', False)
            #     purchase_obj.redeemed_amount = get_decimal(
            #         request_data, 'redeemed_amount')
            #     purchase_obj.redeemed_points = get_decimal(
            #         request_data, 'redeemed_points')
            #     purchase_obj.payable_amount = get_decimal(
            #         request_data, 'payable_amount')
            #     purchase_obj.available_amount = get_decimal(
            #         request_data, 'available_amount')
            #     purchase_obj.available_points = get_decimal(
            #         request_data, 'available_points')
            #     purchase_obj.redemption_amount = get_decimal(
            #         request_data, 'redemption_amount')
            #     purchase_obj.is_full_redemption = request_data.get(
            #         'is_full_redemption', False)
            #     purchase_obj.amount = request_data.get(
            #         'amount', 0)
            #     purchase_obj.customer_email = request_data.get(
            #         'customer_email', "")
            #     purchase_obj.redemption_method = request_data.get(
            #         'redemption_method', "")
            #     purchase_obj.save()
            #
            # else:
            #     PurchaseRequest.objects.create(
            #         request_id=request_data.get(
            #             'request_id', None),
            #         invoice=invoice,
            #         reference_id=request_data.get(
            #             'reference_id', None),
            #         card_number=request_data.get(
            #             'card_number', None),
            #         card_expiry=request_data.get(
            #             'card_expiry', None),
            #         encrypted_card_number=request_data.get(
            #             'encrypted_card_number', None),
            #         encrypted_card_expiry=request_data.get(
            #             'encrypted_card_expiry', None),
            #         platform=request_data.get(
            #             'platform', None),
            #         customer_name=request_data.get(
            #             'customer_name', None),
            #         amount=get_decimal(
            #             request_data, 'amount'),
            #         currency=request_data.get('currency', None),
            #         amount_in_aed=get_decimal(
            #             request_data, 'amount_in_aed'),
            #         redemption_amount=get_decimal(
            #             request_data, 'redemption_amount'),
            #         redeemed_amount=get_decimal(
            #             request_data, 'redeemed_amount'),
            #         redeemed_points=get_decimal(
            #             request_data, 'redeemed_points'),
            #         payable_amount=get_decimal(
            #             request_data, 'payable_amount'),
            #         available_amount=get_decimal(
            #             request_data, 'available_amount'),
            #         available_points=get_decimal(
            #             request_data, 'available_points'),
            #         is_full_redemption=request_data.get(
            #             'is_full_redemption', False),
            #         redemption_status=request_data.get(
            #             'redemption_status', False),
            #         payment_status=request_data.get(
            #             'payment_status', False),
            #         redemption_method=request_data.get(
            #             'redemption_method', None),
            #         customer_email=request_data.get(
            #             'customer_email',None))
            response_data = {'message': "B2cpayback webhook listener "
                                        "successfully processed data",
                             'status': True}
            logger.info("B2cpayback webhook successfully processed data"
                        "for invoice {}".format(invoice))
            return self.pg_response('HTTP_200_OK', data=response_data)
        except Exception as e:
            logger.error("B2cpayback webhook processing "
                         "failed with error {}".format(e), exc_info=e)
            response_data = {'message': "Data not  updated", 'status': False}
            return self.pg_response('HTTP_500_INTERNAL_SERVER_ERROR',
                                    data=response_data)

    def pg_response(self, code='HTTP_200_OK', data=None):
        return Response(
            headers={'status': getattr(status, code)},
            status=getattr(status, code),
            data={
                'status': getattr(status, code),
                'data': data
            },
            content_type='application/json'
        )
