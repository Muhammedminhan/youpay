import logging

from datetime import timedelta
from decimal import Decimal
from celery import shared_task

from adcbpgclient.models import ADCBTransactionData
from payments.models import YouPayTransactionData, ClientNotification
from integrations.models import GatewayChargeConfiguration
from payments.constants import (
    PAYMENT_STATUS_INITIATED, PAYMENT_STATUS_PENDING, PAYMENT_STATUS_EXPIRED,
    TRANSACTION_EXPIRE_TIME, PAYMENT_METHOD_TOUCHPOINTS_AND_CARD,
    PAYMENT_METHOD_ADCB_CARD_ONLY,
    PAYMENT_METHOD_TOUCHPOINTS
)
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


@shared_task(name='calculate_checkoutpg_gateway_charge')
def calculate_checkoutpg_gateway_charge(**kwargs):
    """
    task to calculate gateway charge based on the
    financial response from checkout pg
    """
    logger.info("checkoutpg gateway charge calculation "
                "started {}".format(kwargs))
    payment_reference = kwargs.get('payment_reference', None)
    financial_action_data = kwargs.get('financial_action_data', None)
    gateway_charge = 0
    try:
        breakdown_types = ["Authorization Fixed Fee",
                           "Authentication Fixed Fee",
                           "Authentication Variable Fee",
                           "Void Fixed Fee",
                           "Gateway Fixed Fee",
                           "Card Verification Fixed Fee"]

        for financial_action in financial_action_data:
            for break_downs in financial_action.get('breakdown'):
                if break_downs.get('breakdown_type') in breakdown_types:
                    gateway_charge += Decimal(
                        break_downs.get('fx_rate_applied', '0.00'))

        transaction_obj = YouPayTransactionData.objects.get(
            payment_reference=payment_reference)
        if transaction_obj:
            transaction_obj.gateway_charge = gateway_charge
            transaction_obj.save()
        return gateway_charge
    except Exception as e:
        logger.error(
            "Unable to store checkoutpg gateway charges for transaction "
            "{} with error {}".format(payment_reference, str(e)))


@shared_task(name='update_calculated_gateway_charges')
def update_calculated_gateway_charges(transaction_id):
    logger.info("storing gateway charge for id {} started"
                "".format(transaction_id))
    if transaction_id:
        transaction_crud_obj = YouPayTransactionCRUD()
        transaction_obj = transaction_crud_obj.get_youpay_transaction_data(
            transaction_id)
        try:
            if transaction_obj:
                gateway_charges = calculate_gateway_charges(transaction_obj)
                if gateway_charges:
                    transaction_obj.gateway_charge = gateway_charges
                    transaction_obj.save()
        except Exception as e:
            logger.error(
                "Unable to store gateway charges for transaction "
                "{} with error {}".format(
                    transaction_obj.transaction_id, str(e)))
        logger.info("storing gateway charge to transaction table completed")


def get_gateway_charges(payment_mode):
    """
    Method used to fetch gateway charges for selected payment mode
    """
    gateway_charge_obj = None
    try:
        gateway_charge_obj = (
            GatewayChargeConfiguration.objects.get(
                payment_mode=payment_mode, is_active=True)
        )
    except (GatewayChargeConfiguration.DoesNotExist, Exception):
        logger.info("No gateway charge instance found for "
                    "{}".format(payment_mode))
    return gateway_charge_obj


def calculate_gateway_charges(transaction_obj):
    """
    Used to calculate gateway charges based on
    the gateway charge configurations
    """
    try:
        amount = transaction_obj.amount
        payment_method = transaction_obj.payment_method

        adcb_card_methods = [PAYMENT_METHOD_TOUCHPOINTS_AND_CARD,
                             PAYMENT_METHOD_ADCB_CARD_ONLY]
        if payment_method in adcb_card_methods:
            adcb_obj = ADCBTransactionData.objects.get(
                reference_id=transaction_obj.payment_reference)
            if (payment_method == PAYMENT_METHOD_TOUCHPOINTS_AND_CARD and
                    adcb_obj.financial_action_response_data):
                redeem_amount = transaction_obj.redeemed_amount
                points_charges = calculate_charge(
                    PAYMENT_METHOD_TOUCHPOINTS, redeem_amount)
                checkoutpg_gateway_charges = (
                    calculate_checkoutpg_gateway_charge(
                        payment_reference=transaction_obj.payment_reference,
                        financial_action_data=
                        adcb_obj.financial_action_response_data
                    ))
                # total amount = adcb charge + card charge
                logger.info("adcb card and points fee charges {} and "
                            "{}".format(checkoutpg_gateway_charges,
                                        points_charges))
                total_charges = (Decimal(points_charges) +
                                 Decimal(checkoutpg_gateway_charges))
                logger.info("total charges for card and points "
                            "{}".format(total_charges))
                return total_charges
            if (payment_method == PAYMENT_METHOD_ADCB_CARD_ONLY and
                    adcb_obj.financial_action_response_data):
                checkoutpg_gateway_charges = (
                    calculate_checkoutpg_gateway_charge(
                        payment_reference=transaction_obj.payment_reference,
                        financial_action_data=
                        adcb_obj.financial_action_response_data
                    ))
                return checkoutpg_gateway_charges
            else:
                logger.info(
                    "Skipping charge calculation for {} as adcb financial "
                    "action response data is not updated".format(
                        transaction_obj.transaction_id))
                return None

        gateway_charges = calculate_charge(payment_method, amount)
        return gateway_charges
    except Exception as e:
        logger.error(
            "Error in calculating gateway charges for {}, with error {}"
            "".format(transaction_obj.transaction_id, str(e)))
        return None


def calculate_charge(payment_method, amount):
    gateway_charge_obj = get_gateway_charges(payment_method)
    gateway_charges = Decimal('0.0')
    if gateway_charge_obj:
        percentage = gateway_charge_obj.percentage
        fixed_amount = gateway_charge_obj.fixed_amount
        if percentage:
            gateway_charges += (amount * Decimal(percentage / 100))
        if fixed_amount:
            gateway_charges += Decimal(fixed_amount)
    return gateway_charges


@shared_task(name='update_financial_action_charges')
def update_financial_action_charges(**kwargs):
    """
    used to update transactiondata table from checkoutpgclient with financial
    action response data breakdowns
    """
    transaction_data_id = kwargs.get('pk', None)
    financial_action_data = kwargs.get('financial_action_data', None)
    if transaction_data_id:
        for financial_action in financial_action_data:
            for break_downs in financial_action.get('breakdown'):
                update_breakdown_fee(transaction_data_id, break_downs)
        logger.info("Updated financial action charge breakdowns "
                    "successfully")


def update_breakdown_fee(transaction_data_id, break_downs):
    from checkoutpgclient.models import TransactionData
    breakdown_type = break_downs.get('breakdown_type')
    if breakdown_type == "Authorization Fixed Fee":
        TransactionData.objects.filter(
            id=transaction_data_id).update(
            gateway_fee_authorization=break_downs.get(
                'holding_currency_amount'))
    elif breakdown_type == "Void Fixed Fee":
        TransactionData.objects.filter(
            id=transaction_data_id).update(
            gateway_fee_void=break_downs.get(
                'holding_currency_amount'))
    elif breakdown_type == "Refund Fixed Fee":
        TransactionData.objects.filter(
            id=transaction_data_id).update(
            gateway_fee_refund=break_downs.get(
                'holding_currency_amount'))
    elif breakdown_type == "Blended Variable Fee":
        TransactionData.objects.filter(
            id=transaction_data_id).update(
            blended_variable_fee=break_downs.get(
                'holding_currency_amount'))
    elif breakdown_type == "Authorization Fixed Fee Tax":
        TransactionData.objects.filter(
            id=transaction_data_id).update(
            gateway_fee_authorization_vat=break_downs.get(
                'holding_currency_amount'))
    elif breakdown_type == "Void Fixed Fee Tax":
        TransactionData.objects.filter(
            id=transaction_data_id).update(
            gateway_fee_void_vat=break_downs.get(
                'holding_currency_amount'))
    elif breakdown_type == "Refund Fixed Fee Tax":
        TransactionData.objects.filter(
            id=transaction_data_id).update(
            gateway_fee_refund_vat=break_downs.get(
                'holding_currency_amount'))
    elif breakdown_type == "Blended Variable Fee Tax":
        TransactionData.objects.filter(
            id=transaction_data_id).update(
            blended_variable_fee_vat=break_downs.get(
                'holding_currency_amount'))
