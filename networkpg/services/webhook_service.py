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

        try:
            tx = NetworkTransaction.objects.filter(
                youpay_transaction__transaction_id=merchant_order_reference).first()
            if not tx:
                tx = NetworkTransaction.objects.filter(network_order_id=order_reference).first()

            if tx:
                notification = EventNotification.objects.create(
                    payment_reference=merchant_order_reference,
                    event_type=event_type,
                    raw_data=raw_data,
                    event_id=raw_data.get('eventId'),
                    network_transaction=tx
                )
                WebhookService._update_transaction_status(tx, raw_data)
                WebhookService._trigger_youpay_update(tx)
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
    def _trigger_youpay_update(tx):
        """
        Updates the main YouPayTransactionData record.
        """

        crud = YouPayTransactionCRUD()

        payment_status = PAYMENT_STATUS_PENDING
        if tx.status in [PaymentStatus.AUTHORIZED, PaymentStatus.CAPTURED]:
            payment_status = PAYMENT_STATUS_PAID
        elif tx.status == PaymentStatus.FAILED:
            payment_status = PAYMENT_STATUS_REJECTED

        data_to_update = {
            'transaction_id': tx.youpay_transaction.transaction_id,
            "payment_status": payment_status,
            "payment_reference": tx.payment_reference,
            "payment_method": PAYMENT_METHOD_NETWORK_CARD,
            "payment_gateway": PAYMENT_GATEWAY_NETWORK_IN
        }

        if tx.card_bin:
            data_to_update.update({
                "card_bin": tx.card_bin,
                "card_last4": tx.card_last4,
                "payment_scheme": capfirst(tx.card_scheme.lower()) if tx.card_scheme else None,
                "name_on_card": tx.card_holder_name,
                "card_issuer_country": tx.card_issuer_country,
                "approved": tx.is_approved
            })

        crud.update_youpay_transaction_data(data_to_update)

    @staticmethod
    def _update_transaction_status(tx, data):
        """
        Maps Network Intl states to local Transaction states.
        """
        event_type = data.get('eventName')

        if event_type == 'CAPTURED':
            tx.status = PaymentStatus.CAPTURED
            tx.is_approved = True
        elif event_type == 'FAILED':
            tx.status = PaymentStatus.FAILED
            tx.is_approved = False
        elif event_type == 'AUTHORISED':
            tx.status = PaymentStatus.AUTHORIZED
            tx.is_approved = True
        elif event_type == 'DECLINED':
            tx.status = PaymentStatus.DECLINED
            tx.is_approved = False

        order_data = data.get('order', {})
        payments = order_data.get('_embedded', {}).get('payment', [])
        if not payments:
            payments = data.get('_embedded', {}).get('payment', [])

        if payments:
            active_payment = payments[0]
            payment_method = active_payment.get('paymentMethod', {})
            pan = payment_method.get('pan', '')

            tx.card_bin = pan[:6] if pan else None
            tx.card_last4 = pan[-4:] if pan else None
            tx.card_scheme = payment_method.get('name')
            tx.card_holder_name = payment_method.get('cardholderName')
            tx.card_expiry_date = payment_method.get('expiry')
            tx.card_issuer_country = payment_method.get('issuingCountry')
            tx.card_type = payment_method.get('cardType')

        tx.save()

        logger.info(
            f"Updated NetworkTransaction {tx.payment_reference} to {tx.status}"
        )
