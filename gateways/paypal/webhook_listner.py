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


def handle_payment_capture_refunded(webhook_data):
    resource = webhook_data.get('resource', {})
    seller_breakdown = resource.get('seller_payable_breakdown', {})
    net_amount_breakdown = seller_breakdown.get('net_amount_breakdown', [{}])[
        0] if seller_breakdown.get('net_amount_breakdown') else {}
    exchange_rate = net_amount_breakdown.get('exchange_rate', {})

    log_entry = PayPalWebhookLog(
        event_id=webhook_data.get('id'),
        event_type=webhook_data.get('event_type'),
        resource_type=webhook_data.get('resource_type'),
        summary=webhook_data.get('summary'),
        status=resource.get('status'),
        invoice_id=resource.get('invoice_id'),
        payment_reference=resource.get('invoice_id'),
        refund_id=resource.get('id'),
        amount_value=resource.get('amount', {}).get('value'),
        amount_currency=resource.get('amount', {}).get('currency_code'),
        paypal_fee=seller_breakdown.get('paypal_fee', {}).get('value'),
        net_amount=seller_breakdown.get('net_amount', {}).get('value'),
        merchant_id=resource.get('payer', {}).get('merchant_id'),
        payee_email=resource.get('payer', {}).get('email_address'),
        total_refunded_amount=seller_breakdown.get('total_refunded_amount',
                                                   {}).get('value'),
        gross_amount=seller_breakdown.get('gross_amount', {}).get('value'),
        exchange_rate=exchange_rate.get('value'),
        source_currency=exchange_rate.get('source_currency'),
        target_currency=exchange_rate.get('target_currency'),
        converted_amount=net_amount_breakdown.get('converted_amount', {}).get(
            'value'),
        payable_or_receivable_amount=net_amount_breakdown.get(
            'payable_amount', {}).get(
            'value'),
        payable_or_receivable_currency_code=net_amount_breakdown.get(
            'payable_amount',
                                                       {}).get(
            'currency_code'),
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
        payment_reference=purchase_unit.get('invoice_id'),
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
    exchange_rate = seller_breakdown.get('exchange_rate', {})

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
        payment_reference=resource.get('invoice_id'),
        amount_value=resource.get('amount', {}).get('value'),
        amount_currency=resource.get('amount', {}).get('currency_code'),
        paypal_fee=seller_breakdown.get('paypal_fee', {}).get('value'),
        net_amount=seller_breakdown.get('net_amount', {}).get('value'),
        gross_amount=seller_breakdown.get('gross_amount', {}).get('value'),
        payable_or_receivable_amount=seller_breakdown.get('receivable_amount',
                                                          {}).get('value'),
        payable_or_receivable_currency_code=seller_breakdown.get(
            'receivable_amount', {}).get('currency_code'),
        exchange_rate=exchange_rate.get('value'),
        source_currency=exchange_rate.get('source_currency'),
        target_currency=exchange_rate.get('target_currency'),
        payload=webhook_data,
    )

    log_entry.save()
    return log_entry


def handle_payment_capture_declined(webhook_data):
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
        payment_reference=resource.get('invoice_id'),
        amount_value=resource.get('amount', {}).get('value'),
        amount_currency=resource.get('amount', {}).get('currency_code'),
        paypal_fee=seller_breakdown.get('paypal_fee', {}).get('value'),
        net_amount=seller_breakdown.get('net_amount', {}).get('value'),
        gross_amount=seller_breakdown.get('gross_amount', {}).get('value'),
        merchant_id=resource.get('payee', {}).get('merchant_id'),
        payee_email=resource.get('payee', {}).get('email_address'),
        payload=webhook_data,
    )

    log_entry.save()
    return log_entry


def handle_customer_dispute_created(webhook_data):
    """
    Handle CUSTOMER.DISPUTE.CREATED webhook event and create log entry.
    """
    resource = webhook_data.get('resource', {})
    disputed_transaction = resource.get('disputed_transactions', [{}])[
        0] if resource.get('disputed_transactions') else {}

    log_entry = PayPalWebhookLog(
        event_id=webhook_data.get('id'),
        event_type=webhook_data.get('event_type'),
        resource_type=webhook_data.get('resource_type'),
        summary=webhook_data.get('summary'),
        dispute_id=resource.get('dispute_id'),
        status=resource.get('status'),
        amount_value=resource.get('dispute_amount', {}).get('value'),
        amount_currency=resource.get('dispute_amount', {}).get(
            'currency_code'),
        allowed_refund_amount=resource.get('refund_details', {}).get(
            'allowed_refund_amount', {}).get('value'),
        buyer_requested_amount=resource.get('offer', {}).get(
            'buyer_requested_amount', {}).get('value'),
        merchant_id=disputed_transaction.get('seller', {}).get('merchant_id'),
        invoice_id=disputed_transaction.get('invoice_number'),
        payload=webhook_data,
    )

    log_entry.save()
    return log_entry


def handle_dispute_updated_webhook(webhook_payload: dict):
    """
    Handles the PayPal CUSTOMER.DISPUTE.UPDATED webhook and logs it to PayPalWebhookLog.
    """

    try:
        resource = webhook_payload.get("resource", {})
        dispute_id = resource.get("dispute_id")
        status = resource.get("status")
        stage = resource.get("dispute_stage")
        invoice_id = resource.get("disputed_transactions", {}).get(
            "invoice_number")
        buyer_info = resource.get("buyer", {})
        buyer_email = buyer_info.get("email_address")
        buyer_name = buyer_info.get("name")
        offer = resource.get("offer", {})
        buyer_requested_amount = offer.get("buyer_requested_amount", {}).get(
            "value")
        buyer_currency = offer.get("buyer_requested_amount", {}).get(
            "currency_code")
        allowed_refund_amount = resource.get("refund_details", {}).get(
            "allowed_refund_amount", {}).get("value")
        seller_offered_amount = offer.get("seller_offered_amount", {}).get(
            "value")

        log_entry = PayPalWebhookLog.objects.create(
            event_id=webhook_payload.get("id"),
            event_type=webhook_payload.get("event_type"),
            resource_type=webhook_payload.get("resource_type"),
            summary=webhook_payload.get("summary"),
            dispute_id=dispute_id,
            status=status,
            intent=stage,
            invoice_id=invoice_id,
            payment_reference=invoice_id,
            payer_email=buyer_email,
            payer_name=buyer_name,
            buyer_requested_amount=buyer_requested_amount,
            payable_or_receivable_currency_code=buyer_currency,
            payload=webhook_payload,
            allowed_refund_amount=allowed_refund_amount,
            seller_offered_amount=seller_offered_amount,
        )

        logger.info(f"Dispute updated log saved for dispute_id={dispute_id}")
        return log_entry

    except Exception as e:
        logger.error("Failed to log dispute updated webhook", exc_info=True)
        return None


def handle_dispute_resolved_webhook(payload):
    """
    Handle PayPal CUSTOMER.DISPUTE.RESOLVED webhook and store details in PayPalWebhookLog.
    """
    try:
        resource = payload.get("resource", {})
        dispute_id = resource.get("dispute_id")
        summary = payload.get("summary")
        event_id = payload.get("id")
        event_type = payload.get("event_type")
        resource_type = payload.get("resource_type")
        dispute_amount = resource.get("dispute_amount", {})
        refund_details = resource.get("refund_details", {})
        offer = resource.get("offer", {})
        disputed_txns = resource.get("disputed_transactions", [])
        transaction = disputed_txns[0] if disputed_txns else {}

        PayPalWebhookLog.objects.create(
            event_id=event_id,
            event_type=event_type,
            resource_type=resource_type,
            summary=summary,
            dispute_id=dispute_id,
            status=transaction.get("transaction_status"),
            payer_email=transaction.get("buyer_email"),
            merchant_id=transaction.get("seller", {}).get("merchant_id"),
            payment_reference=transaction.get("invoice_number"),
            invoice_id=transaction.get("invoice_number"),
            amount_value=dispute_amount.get("value"),
            amount_currency=dispute_amount.get("currency_code"),
            allowed_refund_amount=refund_details.get("allowed_refund_amount",
                                                     {}).get("value"),
            buyer_requested_amount=offer.get("buyer_requested_amount",
                                             {}).get("value"),
            seller_offered_amount=offer.get(
                "seller_offered_amount", {}).get("value"),
            payload=payload
        )
    except Exception as e:
        logger.error(
            "Error storing PayPal CUSTOMER.DISPUTE.RESOLVED webhook: %s",
            str(e), exc_info=True)


WEBHOOK_EVENT_HANDLERS = {
    "CHECKOUT.ORDER.APPROVED": handle_checkout_order_approved,
    "PAYMENT.CAPTURE.COMPLETED": handle_payment_capture_completed,
    "PAYMENT.CAPTURE.REFUNDED": handle_payment_capture_refunded,
    "PAYMENT.CAPTURE.DECLINED": handle_payment_capture_declined,
    "CUSTOMER.DISPUTE.UPDATED": handle_dispute_updated_webhook,
    "CUSTOMER.DISPUTE.CREATED": handle_customer_dispute_created,
    "CUSTOMER.DISPUTE.RESOLVED": handle_dispute_resolved_webhook
}
