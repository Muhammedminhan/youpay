import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from gateways.paypal.models import PayPalWebhookLog

logger = logging.getLogger(__name__)

class WebhookListner(APIView):

    def post(self, request):
        try:
            request_data = request.data
            logger.info("Webhook received for PayPal: %s", request_data)

            resource = request_data.get("resource", {})
            payer = resource.get("payer", {})
            name = payer.get("name", {})
            captures = (
                resource.get("purchase_units", [{}])[0]
                .get("payments", {}).get("captures", [{}])
            )
            capture = captures[0] if captures else {}

            seller_breakdown = capture.get("seller_receivable_breakdown", {})

            log_obj = PayPalWebhookLog.objects.create(
                event_id=request_data.get("id"),
                event_type=request_data.get("event_type"),
                resource_type=request_data.get("resource_type"),
                summary=request_data.get("summary"),
                order_id=resource.get("id"),
                status=resource.get("status"),
                intent=resource.get("intent"),
                payer_id=payer.get("payer_id"),
                payer_email=payer.get("email_address"),
                payer_name=f"{name.get('given_name', '')} {name.get('surname', '')}".strip(),
                capture_id=capture.get("id"),
                capture_status=capture.get("status"),
                invoice_id=capture.get("invoice_id"),
                payment_reference=capture.get("invoice_id"),
                amount_value=capture.get("amount", {}).get("value"),
                amount_currency=capture.get("amount", {}).get(
                    "currency_code"),
                paypal_fee=seller_breakdown.get("paypal_fee", {}).get(
                    "value"),
                net_amount=seller_breakdown.get("net_amount", {}).get(
                    "value"),
                payload=request_data
            )

            logger.info("PayPal webhook successfully processed")

            return self.pg_response('HTTP_200_OK', data={
                'message': "PayPal webhook listener successfully processed data",
                'status': True
            })

        except Exception as e:
            logger.error("Error while handling PayPal webhook: %s", e)
            return self.pg_response('HTTP_500_INTERNAL_SERVER_ERROR', data={
                'message': "Data not updated", 'status': False
            })

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
