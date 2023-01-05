import logging

from datetime import timedelta
from celery import shared_task
from payments.models import YouPayTransactionData, ClientNotification
from payments.constants import (PAYMENT_STATUS_INITIATED,
                                PAYMENT_STATUS_PENDING,
                                PAYMENT_STATUS_EXPIRED,
                                TRANSACTION_EXPIRE_TIME)
from django.db.models.functions import Now
from core.utils import wait_redis_lock
from django.db import transaction
from services.v1.views.common import YouPayTransactionCRUD

logger = logging.getLogger(__name__)


@shared_task(name='set_transaction_expired')
def set_transaction_expired():
    """
        Method to set payment_status of all YouPayTransactionData objects
        older than 20 minutes to expired status.
    """
    logger.info("cronjob for setting youpay transactions older than 20 "
                "minutes to expired status started")
    lock_name = 'lock:expire_payment_cronjob:id %s' % (
        set_transaction_expired.request.id)
    try:
        with wait_redis_lock(lock_name=lock_name):
            payment_statuses = [PAYMENT_STATUS_INITIATED,
                                PAYMENT_STATUS_PENDING]
            transaction_objs = YouPayTransactionData.objects.filter(
                payment_status__in=payment_statuses,
                updated_at__lt=Now()-timedelta(
                    minutes=TRANSACTION_EXPIRE_TIME))
            if transaction_objs:
                transaction_ids = []
                for obj in transaction_objs:
                    transaction_ids.append(str(obj.transaction_id))
                    obj.payment_status = PAYMENT_STATUS_EXPIRED
                    obj.save()
                logger.info("cronjob has set transactions {} to expired "
                            "status".format(transaction_ids))
            return True
    except Exception as e:
        logger.error("Error occurred during expire payment cronjob",
                     exc_info=e)


@shared_task(name='client_event_notification_logging')
def client_event_notification_logging(transaction_id, status):
    logger.info("storing client event notification for id {} status"
                " started".format(transaction_id))
    event_type = None
    if transaction_id:
        transaction_crud_obj = YouPayTransactionCRUD()
        transaction_obj = transaction_crud_obj.get_youpay_transaction_data(
            transaction_id)
        try:
            if transaction_obj:
                payment_status = transaction_obj.payment_status
                lock_name = ('lock:client_event_notification_logging:'
                             'transaction_pk_%d' % transaction_obj.id)
                with wait_redis_lock(lock_name=lock_name):
                    with transaction.atomic():
                        process_notification_data(transaction_obj,
                                                  payment_status, status)
                        logger.info("Client notification logged transaction "
                                    "{}".format(transaction_id))
            else:
                logger.error("Unable to find the transaction while "
                             "logging client event notification "
                             "{}".format(transaction_id))
        except Exception as e:
            logger.error(
                "Unable to store client event notification log for "
                "transaction {} with error {}".format(
                    transaction_obj.transaction_id, e))
        logger.info("storing client event notification log completed")


def process_notification_data(transaction_obj, payment_status, status):
    try:
        notification = (
            ClientNotification.objects.select_for_update().
            get(transaction=transaction_obj,
                payment_status=payment_status))
    except ClientNotification.DoesNotExist:
        notification = None
    except ClientNotification.MultipleObjectsReturned:
        notification = (
            ClientNotification.objects.filter(
                transaction=transaction_obj,
                payment_status=payment_status)
            .order_by('-created_at')[0])
    if notification:
        notification.is_notified = status if status else False
        notification.notification_response_status = status
        notification.save()
    else:
        ClientNotification.objects.create(
            transaction=transaction_obj,
            api_client=transaction_obj.api_client,
            payment_status=payment_status,
            is_notified=status if status else False,
            notification_response_status=status
        )
