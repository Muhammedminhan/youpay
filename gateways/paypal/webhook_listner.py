import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from gateways.paypal.authentication import PayPalWebhookAuthentication
from gateways.paypal.models import PayPalWebhookLog

logger = logging.getLogger(__name__)

class WebhookListner(APIView):
    authentication_classes = (PayPalWebhookAuthentication,)

    def post(self, request):
        request_data = request.data
        event_type = request_data.get("event_type")
        logger.info(
            "PayPal webhook received for event {}: with data: {}".format(
                event_type, request_data))

        handler = WEBHOOK_EVENT_HANDLERS.get(event_type)
        if not handler:
            logger.error(f"No handler for PayPal event: {event_type}")
            return Response(status=status.HTTP_204_NO_CONTENT)

        try:
            handler(request_data)
            return Response(
                {"message": "Webhook processed", "status": True},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Error processing webhook {event_type}: {e}")
            return Response(
                {"message": "Webhook error", "status": False},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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


def handle_payment_refund_completed(webhook_data):
    resource = webhook_data.get('resource', {})
    seller_breakdown = resource.get('seller_payable_breakdown', {})

    log_entry = PayPalWebhookLog(
        event_id=webhook_data.get('id'),
        event_type=webhook_data.get('event_type'),
        resource_type=webhook_data.get('resource_type'),
        summary=webhook_data.get('summary'),
        order_id=resource.get('supplementary_data', {}).get(
            'related_ids', 'order_id'),
        status=resource.get('status'),
        capture_id=resource.get('capture_id'),
        invoice_id=resource.get('invoice_id'),
        amount_value=resource.get('amount', {}).get('value'),
        amount_currency=resource.get('amount', {}).get('currency_code'),
        paypal_fee=seller_breakdown.get('paypal_fee', {}).get('value'),
        net_amount=seller_breakdown.get('net_amount', {}).get('value'),
        payload=webhook_data,
    )

    log_entry.save()
    return log_entry


def handle_checkout_order_approved(webhook_data):
    event_data = webhook_data.get('resource', {})
    purchase_unit = event_data.get('purchase_units', [{}])[
        0] if event_data.get('purchase_units') else {}
    payer_data = event_data.get('payer', {})
    payer_name = payer_data.get('name', {})
    payment_source = event_data.get('payment_source', {}).get('paypal', {})

    log_entry = PayPalWebhookLog(
        event_id=webhook_data.get('id'),
        event_type=webhook_data.get('event_type'),
        resource_type=webhook_data.get('resource_type'),
        summary=webhook_data.get('summary'),
        order_id=event_data.get('id'),
        status=event_data.get('status'),
        intent=event_data.get('intent'),
        payer_id=payer_data.get('payer_id') or payment_source.get(
            'account_id'),
        payer_email=payer_data.get('email_address') or payment_source.get(
            'email_address'),
        payer_name=f"{payer_name.get('given_name', '')} {payer_name.get('surname', '')}".strip(),
        invoice_id=purchase_unit.get('invoice_id'),
        merchant_id=purchase_unit.get('payee', {}).get('merchant_id'),
        payee_email=purchase_unit.get('payee', {}).get('email_address'),
        amount_value=purchase_unit.get('amount', {}).get('value'),
        amount_currency=purchase_unit.get('amount', {}).get('currency_code'),
        payload=webhook_data,
    )

    log_entry.save()
    return log_entry


def handle_payment_capture_completed(webhook_data):
    resource = webhook_data.get('resource', {})
    seller_breakdown = resource.get('seller_receivable_breakdown', {})

    log_entry = PayPalWebhookLog(
        event_id=webhook_data.get('id'),
        event_type=webhook_data.get('event_type'),
        resource_type=webhook_data.get('resource_type'),
        summary=webhook_data.get('summary'),
        order_id=resource.get('supplementary_data', {}).get('related_ids',
                                                            {}).get(
            'order_id'),
        status=resource.get('status'),
        capture_id=resource.get('id'),
        capture_status=resource.get('status'),
        invoice_id=resource.get('invoice_id'),
        amount_value=resource.get('amount', {}).get('value'),
        amount_currency=resource.get('amount', {}).get('currency_code'),
        paypal_fee=seller_breakdown.get('paypal_fee', {}).get('value'),
        net_amount=seller_breakdown.get('net_amount', {}).get('value'),
        payload=webhook_data,
    )

    log_entry.save()
    return log_entry


WEBHOOK_EVENT_HANDLERS = {
    "CHECKOUT.ORDER.APPROVED": handle_checkout_order_approved,
    "PAYMENT.CAPTURE.COMPLETED": handle_payment_capture_completed,
    "PAYMENT.REFUND.COMPLETED": handle_payment_refund_completed,
}
