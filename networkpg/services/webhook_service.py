import logging
from django.utils import timezone
from networkpg.models import NetworkTransaction, EventNotification
from networkpg.choices import PaymentStatus

logger = logging.getLogger(__name__)

class WebhookService:
    @staticmethod
    def process_event(raw_data):
        """
        Master method to handle incoming webhook events.
        """
        event_type = raw_data.get('eventName') # Network Intl often uses eventName
        order_reference = raw_data.get('order', {}).get('reference')
        merchant_order_reference = raw_data.get('order', {}).get('merchantOrderReference')

        # Store notification for audit
        notification = EventNotification.objects.create(
            payment_reference=merchant_order_reference,
            event_type=event_type,
            raw_data=raw_data
        )

        try:
            # Find the transaction
            tx = NetworkTransaction.objects.filter(payment_reference=merchant_order_reference).first()
            if not tx:
                # Fallback to network order ID
                tx = NetworkTransaction.objects.filter(network_order_id=order_reference).first()

            if tx:
                WebhookService._update_transaction_status(tx, raw_data)
                notification.processed = True
                notification.processed_at = timezone.now()
                notification.save()
                return True
            else:
                logger.warning(f"No transaction found for webhook: {merchant_order_reference} / {order_reference}")
                notification.error_message = "Transaction record not found"
                notification.save()
                return False

        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
            notification.error_message = str(e)
            notification.save()
            return False

    @staticmethod
    def _update_transaction_status(tx, data):
        """
        Maps Network Intl states to local Transaction states.
        """
        # Network Intl status is often nested in order/payment
        # For simplicity, we assume a standard layout, but in reality, need to check specific event types
        event_type = data.get('eventName')
        
        # Example mappings (Check actual docs for payload structure)
        if event_type == 'PAYMENT_CAPTURED':
            tx.status = PaymentStatus.CAPTURED
            tx.is_approved = True
        elif event_type == 'PAYMENT_FAILED':
            tx.status = PaymentStatus.FAILED
            tx.is_approved = False
        elif event_type == 'AUTHORISATION_SUCCESSFUL':
            tx.status = PaymentStatus.AUTHORIZED
            tx.is_approved = True
        elif event_type == 'AUTHORISATION_FAILED':
            tx.status = PaymentStatus.DECLINED
            tx.is_approved = False

        # Extract card info if available
        payment_info = data.get('payment', {})
        if payment_info:
            tx.card_bin = payment_info.get('_embedded', {}).get('payment:card-info', {}).get('bin')
            tx.card_last4 = payment_info.get('_embedded', {}).get('payment:card-info', {}).get('last4Digits')
            tx.card_scheme = payment_info.get('_embedded', {}).get('payment:card-info', {}).get('scheme')

        tx.save()
        
        # Proactive: Here you would typically trigger something like updating the main 'youpay' transaction
        # Similar to checkoutpg logic.
        logger.info(f"Updated NetworkTransaction {tx.payment_reference} to {tx.status}")
