import logging
from datetime import timedelta
from decimal import Decimal
import requests

from celery import shared_task
from django.db import transaction
from django.db.models.functions import Now
from django.conf import settings
from django.db.models import Q

from adcbpgclient.models import ADCBTransactionData
from core.utils import wait_redis_lock
from integrations.models import GatewayChargeConfiguration
from payments.constants import (
    PAYMENT_STATUS_EXPIRED,
    TRANSACTION_EXPIRE_TIME, PAYMENT_METHOD_TOUCHPOINTS_AND_CARD,
    PAYMENT_METHOD_ADCB_CARD_ONLY,
    PAYMENT_METHOD_TOUCHPOINTS, ALLOW_EXPIRE_STATUS_LIST,
    MODEL_NAME_TRANSACTIONDATA, MODEL_NAME_ADCBTRANSACTIONDATA,
    AUTHORIZATION_FIXED_FEE, VOID_FIXED_FEE, REFUND_FIXED_FEE,
    BLENDED_VARIABLE_FEE, AUTHORIZATION_FIXED_FEE_TAX, VOID_FIXED_FEE_TAX,
    REFUND_FIXED_FEE_TAX, BLENDED_VARIABLE_FEE_TAX,
    GROUPGIFT_ORDER_ID_ENDPOINT
)
from payments.models import YouPayTransactionData, ClientNotification
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
            transaction_objs = YouPayTransactionData.objects.filter(
                payment_status__in=ALLOW_EXPIRE_STATUS_LIST,
                updated_at__lt=Now() - timedelta(
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
    payment_reference = kwargs.get('payment_reference', None)
    logger.info("checkoutpg gateway charge calculation "
                "started for {}".format(payment_reference))
    gateway_charge = 0
    try:
        transaction_obj = YouPayTransactionData.objects.get(
            payment_reference=payment_reference)
        if transaction_obj:
            transaction_obj.gateway_charge = gateway_charge
            transaction_obj.save()
            logger.info("Successfully saved gateway charge for reference "
                        "{}".format(payment_reference))
        return gateway_charge

    except YouPayTransactionData.DoesNotExist:
        logger.info(
            "Unable to store YouPayTransactionData with payment reference {}"
            " to store checkoutpg gateway charges".format(payment_reference))

    except Exception as e:
        logger.error(
            "Unable to store checkoutpg gateway charges for transaction "
            "{} with error {}".format(payment_reference, str(e)))


@shared_task(name='update_calculated_gateway_charges')
def update_calculated_gateway_charges(transaction_id):
    logger.info("storing gateway charge for id {} started"
                "".format(transaction_id))
    message = None
    if transaction_id:
        try:
            transaction_crud_obj = YouPayTransactionCRUD()
            transaction_obj = transaction_crud_obj.get_youpay_transaction_data(
                transaction_id)
            if transaction_obj:
                gateway_charges = calculate_gateway_charges(transaction_obj)
                if gateway_charges:
                    transaction_obj.gateway_charge = gateway_charges
                    transaction_obj.save()
                    message = "Transaction object saved"
                else:
                    message = "No Gateway charges"
            else:
                message = "No transaction_obj"

        except Exception as e:
            message = ("Unable to store gateway charges for transaction "
                       "{} with error {}".format(transaction_id, str(e)))
            logger.error(message)

    logger.info(
        "storing gateway charge to transaction table completed for {}, {}"
        "".format(transaction_id, message))


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
                            "{} for transaction {}".format(
                    checkoutpg_gateway_charges,
                    points_charges, transaction_obj.transaction_id))
                total_charges = (Decimal(points_charges) +
                                 Decimal(checkoutpg_gateway_charges))
                logger.info(
                    "total charges for card and points for transaction  "
                    "{} is {}".format(transaction_obj.transaction_id,
                                      total_charges))
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


@shared_task(name='common_update_financial_action_charges')
def common_update_financial_action_charges(**kwargs):
    """
        used to update client table of checkoutpg or b2cpayback with
        financial action response data breakdowns
        """
    model_name = kwargs.get('model_name', None)
    try:
        logger.info(
            "Updating {} with received financial action response data "
            "breakups".format(model_name))
        if model_name == MODEL_NAME_TRANSACTIONDATA:
            from checkoutpgclient.models import TransactionData
            model_name = TransactionData
        if model_name == MODEL_NAME_ADCBTRANSACTIONDATA:
            from adcbpgclient.models import ADCBTransactionData
            model_name = ADCBTransactionData
        transaction_data_id = kwargs.get('pk', None)
        financial_action_data = kwargs.get('financial_action_data', None)
        if transaction_data_id:
            first_iteration = True
            for financial_action in financial_action_data:
                if first_iteration:
                    model_name.objects.filter(
                        id=transaction_data_id).update(
                        card_category=financial_action.get("card_category"),
                        entity_id=financial_action.get("entity_id"),
                        card_issuer_country=financial_action.get(
                            'issuer_country'))
                    first_iteration = False
                for break_downs in financial_action.get('breakdown'):
                    common_update_breakdown_fee(model_name,
                                                transaction_data_id,
                                                break_downs)
            logger.info("Updated financial action charge breakdowns in "
                        "{} successfully for transaction "
                        "{}".format(model_name, transaction_data_id))
    except Exception as e:
        logger.error(
            "Error updating financial action response charges for"
            " {}".format(model_name), exc_info=e)


def common_update_breakdown_fee(model_name, transaction_data_id, break_downs):
    breakdown_type = break_downs.get('breakdown_type')
    if breakdown_type == AUTHORIZATION_FIXED_FEE:
        model_name.objects.filter(
            id=transaction_data_id).update(
            gateway_fee_authorization=break_downs.get(
                'holding_currency_amount'))
    elif breakdown_type == VOID_FIXED_FEE:
        model_name.objects.filter(
            id=transaction_data_id).update(
            gateway_fee_void=break_downs.get(
                'holding_currency_amount'))
    elif breakdown_type == REFUND_FIXED_FEE:
        model_name.objects.filter(
            id=transaction_data_id).update(
            gateway_fee_refund=break_downs.get(
                'holding_currency_amount'))
    elif breakdown_type == BLENDED_VARIABLE_FEE:
        model_name.objects.filter(
            id=transaction_data_id).update(
            blended_variable_fee=break_downs.get(
                'holding_currency_amount'))
    elif breakdown_type == AUTHORIZATION_FIXED_FEE_TAX:
        model_name.objects.filter(
            id=transaction_data_id).update(
            gateway_fee_authorization_vat=break_downs.get(
                'holding_currency_amount'))
    elif breakdown_type == VOID_FIXED_FEE_TAX:
        model_name.objects.filter(
            id=transaction_data_id).update(
            gateway_fee_void_vat=break_downs.get(
                'holding_currency_amount'))
    elif breakdown_type == REFUND_FIXED_FEE_TAX:
        model_name.objects.filter(
            id=transaction_data_id).update(
            gateway_fee_refund_vat=break_downs.get(
                'holding_currency_amount'))
    elif breakdown_type == BLENDED_VARIABLE_FEE_TAX:
        model_name.objects.filter(
            id=transaction_data_id).update(
            blended_variable_fee_vat=break_downs.get(
                'holding_currency_amount'))


@shared_task(name='fetch_groupgift_order_id')
def fetch_groupgift_order_id():
    """
    task to collect order id from groupgift for payment references in youpay
    and update order id at youpaytransactiondata
    """
    environment = settings.ENVIRONMENT
    client_name = str(get_groupgift_client_name(environment))
    logger.info(
        "running task for fetching groupgift order id, environment is "
        "{}, youpay client name {}".format(environment, client_name))
    transaction_objects = YouPayTransactionData.objects.filter(
        api_client__name=client_name).exclude(
        order_id__startswith="ECMGRPGFT_")[:10]
    references_list = []
    groupgift_order_id_endpoint = GROUPGIFT_ORDER_ID_ENDPOINT
    try:
        groupgift_domain = ''
        first_iteration = True
        for transaction_obj in transaction_objects:
            if first_iteration:
                groupgift_domain = transaction_obj.api_client.client_domain
                first_iteration = False
            if not transaction_obj.payment_reference:
                continue
            references_list.append(str(transaction_obj.payment_reference))
        if len(references_list) > 0:
            references_dict = {"references": references_list}
            groupgift_formatted_url = (
                    groupgift_domain + groupgift_order_id_endpoint)
            logger.info(
                "references passed for fetching order id from groupgift {}"
                "-->>{}".format(
                    groupgift_formatted_url, references_dict))
            response = requests.post(
                url=groupgift_formatted_url, json=references_dict)
            if response:
                response_data = response.json()
                if len(response_data):
                    logger.info(
                        "response received from groupgift endpoint {}".format(
                            response_data))
                    updated = update_youpaytransactiondata_order_id(
                        response_data)
                    return updated
            logger.error(
                "Invalid response received from groupgift {}".format(
                    response.text))
            return False
        else:
            logger.info(
                "No groupgift transactions found having empty order_id")
            return False
    except Exception as e:
        logger.error(
            "Error occurred while fetching order id from groupgift {}, with"
            " request data {}, error - {}".format(
                groupgift_order_id_endpoint, references_list, e), exc_info=e)
        return False


def get_groupgift_client_name(environment):
    """
    takes environment value from settings and returns corresponding
    group gift client name
    """
    if environment == 'sandbox':
        client_name = 'Group Gift Sandbox'
    elif environment == 'production':
        client_name = 'eCom Group Gift Production'
    else:
        client_name = 'Group Gift QA'
    return client_name


def update_youpaytransactiondata_order_id(response_data):
    """
    method to update youpaytransactiondata with order ids.
    Takes response data list of dict as input and parses the data for
    order id corresponding to each payment reference and updates the value in
    order_id field
    """
    try:
        reference_numbers = [item['reference_number'] for item in
                             response_data if len(item['order_id']) > 0]
        if len(reference_numbers):
            objects_to_update = YouPayTransactionData.objects.filter(
                payment_reference__in=reference_numbers)
            data_dict = {item['reference_number']: item['order_id'] for
                         item in response_data}
            for obj in objects_to_update:
                obj.order_id = data_dict.get(obj.payment_reference)
            updated = YouPayTransactionData.objects.bulk_update(
                objects_to_update, ['order_id'])
            logger.info(
                "Successfully updated order ids for {} bulk update updated {}"
                " entries".format(reference_numbers, updated))
            return True
        logger.info(
            "Skipping updating groupgift order id as references to update "
            "is 0")
        return False
    except Exception as e:
        logger.error(
            "Exception occurred during updating order ids, {}".format(e),
            exc_info=e)
        return False
