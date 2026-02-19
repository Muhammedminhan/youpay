import logging
from django.utils import timezone
from networkpg.models import NetworkTransaction, EventNotification
from services.v1.views.common import YouPayTransactionCRUD
from networkpg.choices import PaymentStatus
from django.utils.text import capfirst
from payments.constants import (
    PAYMENT_STATUS_PAID,
    PAYMENT_STATUS_PENDING,
    PAYMENT_STATUS_REJECTED,
    PAYMENT_METHOD_NETWORK_CARD,
    PAYMENT_STATUS_DECLINED,
    PAYMENT_STATUS_FAILED
)
from core.constants import PAYMENT_GATEWAY_NETWORK_IN
logger = logging.getLogger(__name__)


class WebhookService:
    @staticmethod
    def process_event(raw_data):
        """
        Master method to handle incoming webhook events.
        """
        event_type = raw_data.get('eventName')
        order_reference = raw_data.get('order', {}).get('reference')
        merchant_order_reference = raw_data.get('order', {}).get('merchantOrderReference')
        notification = EventNotification.objects.create(
            payment_reference=merchant_order_reference,
            event_type=event_type,
            raw_data=raw_data,
            event_id=raw_data.get('eventId'),
        )
        try:
            transaction_obj = NetworkTransaction.objects.filter(
                youpay_transaction__transaction_id=merchant_order_reference).first()
            if not transaction_obj:
                transaction_obj = NetworkTransaction.objects.filter(network_order_id=order_reference).first()

            if transaction_obj:
                notification.network_transaction = transaction_obj
                WebhookService._update_transaction_status(transaction_obj, raw_data)
                WebhookService._trigger_youpay_update(transaction_obj)
                notification.processed = True
                notification.processed_at = timezone.now()
                notification.save()
                return True
            else:
                logger.warning(
                    f"No transaction found for webhook: {merchant_order_reference} / {order_reference}"
                )
                notification.error_message = "Transaction record not found"
                notification.save()
                return False

        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
            notification.error_message = str(e)
            notification.save()
            return False

    @staticmethod
    def _trigger_youpay_update(transaction_obj):
        """
        Updates the main YouPayTransactionData record.
        """

        crud = YouPayTransactionCRUD()

        payment_status = PAYMENT_STATUS_PENDING
        if transaction_obj.status in [PaymentStatus.AUTHORIZED, PaymentStatus.CAPTURED]:
            payment_status = PAYMENT_STATUS_PAID
        elif transaction_obj.status == PaymentStatus.FAILED:
            payment_status = PAYMENT_STATUS_FAILED
        elif transaction_obj.status in [PaymentStatus.DECLINED]:
            payment_status = PAYMENT_STATUS_DECLINED

        data_to_update = {
            'transaction_id': transaction_obj.youpay_transaction.transaction_id,
            "payment_status": payment_status,
            "payment_reference": transaction_obj.payment_reference,
            "payment_method": PAYMENT_METHOD_NETWORK_CARD,
            "payment_gateway": PAYMENT_GATEWAY_NETWORK_IN
        }

        if transaction_obj.card_bin:
            data_to_update.update({
                "card_bin": transaction_obj.card_bin,
                "card_last4": transaction_obj.card_last4,
                "payment_scheme": capfirst(transaction_obj.card_scheme.lower()) if transaction_obj.card_scheme else None,
                "name_on_card": transaction_obj.card_holder_name,
                "card_issuer_country": transaction_obj.card_issuer_country,
                "approved": transaction_obj.is_approved
            })

        crud.update_youpay_transaction_data(data_to_update)

    @staticmethod
    def _update_transaction_status(transaction_obj, data):
        """
        Maps Network Intl states to local Transaction states.
        """
        event_type = data.get('eventName')

        if event_type == 'CAPTURED':
            transaction_obj.status = PaymentStatus.CAPTURED
            transaction_obj.is_approved = True
        elif event_type in ['FAILED',]:
            transaction_obj.status = PaymentStatus.FAILED
            transaction_obj.is_approved = False
        elif event_type == 'AUTHORISED':
            transaction_obj.status = PaymentStatus.AUTHORIZED
            transaction_obj.is_approved = True
        elif event_type in ['THREE_DS_NOT_AUTHENTICATED', 'DECLINED',
                            'AUTHORISATION_FAILED']:
            transaction_obj.status = PaymentStatus.DECLINED
            transaction_obj.is_approved = False

        order_data = data.get('order', {})
        payments = order_data.get('_embedded', {}).get('payment', [])
        if not payments:
            payments = data.get('_embedded', {}).get('payment', [])

        if payments:
            active_payment = payments[0]
            payment_method = active_payment.get('paymentMethod', {})
            card_number = payment_method.get('pan', '')

            transaction_obj.card_bin = card_number[:6] if card_number else None
            transaction_obj.card_last4 = card_number[-4:] if card_number else None
            transaction_obj.card_scheme = payment_method.get('name')
            transaction_obj.card_holder_name = payment_method.get('cardholderName')
            transaction_obj.card_expiry_date = payment_method.get('expiry')
            transaction_obj.card_issuer_country = payment_method.get('issuingCountry')
            transaction_obj.card_type = payment_method.get('cardType')

        transaction_obj.save()

        logger.info(
            f"Updated NetworkTransaction {transaction_obj.payment_reference} to {transaction_obj.status}"
        )
