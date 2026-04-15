import logging

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from payments.constants import (MODEL_NAME_TRANSACTIONDATA,
                                CARD_BIN_MAX_LENGTH,
                                PAYMENT_SCHEME_AMERICAN_EXPRESS)
from payments.tasks import (common_update_financial_action_charges)
from services.v1.views.utils import (is_rewards_order_reference,
                                    get_checkout_amex_additional_fee)
from .constants import (PAYMENT_STATUS_CHOICES, PAYMENT_STATUS_NONE,
                        PAYMENT_METHOD_CHOICES,
                        PAYMENT_METHOD_CARD, PAYMENT_SCHEME_CHOICES,
                        PAYMENT_SCHEME_NONE,
                        ALLOWED_STATUS_FOR_YOUPAY_WEBHOOK_UPDATE,
                        PAYMENT_STATUS_PAID)
from core.utils import get_gateway_additional_fee
from integrations.constants import (ADDITIONAL_AMEX_CARD_FEE,
                                    CHECKOUTPG_HUB_CODE)

logger = logging.getLogger(__name__)


class TransactionData(models.Model):
    created_on = models.DateTimeField(auto_now_add=True)
    modified_on = models.DateTimeField(auto_now=True)
    order_reference = models.CharField(max_length=200)
    amount = models.DecimalField(decimal_places=4, max_digits=12,
                                 db_index=True)
    currency = models.CharField(max_length=3, db_index=True)
    customer_name = models.CharField(max_length=200)
    customer_email = models.CharField(max_length=500, db_index=True)
    idempotency_key = models.CharField(
        max_length=200, blank=False, default=None,
        help_text='Unique key to avoid duplicate payment happening due to '
                  'network error or timeout. Recommend to use V4 UUIDs.')
    payment_reference = models.CharField(
        max_length=200, blank=False, db_index=True,
        help_text='Payment reference number')
    request_source = models.CharField(
        max_length=100, null=True, blank=True,
        help_text='Represent source from where this payment request '
                  'initiated')
    api_request_data = models.TextField(
        null=True, blank=True, help_text='Payment API request data')
    api_response_data = models.TextField(
        null=True, blank=True, help_text='Payment API response data')
    is_notification = models.BooleanField(default=False)
    approved = models.BooleanField(
        default=False,
        help_text='Denotes whether the payment is approved or not')
    status = models.CharField(max_length=200, choices=PAYMENT_STATUS_CHOICES,
                              default=PAYMENT_STATUS_NONE, db_index=True,
                              help_text='Payment status')
    auth_code = models.CharField(
        max_length=50, null=True, blank=True,
        help_text='The acquirer authorization code, if the payment '
                  'was authorized.')
    response_summary = models.CharField(
        max_length=500, null=True, blank=True,
        help_text='Checkout response summary text')
    invoice_id = models.CharField(
        max_length=50, null=True, blank=True, db_index=True,
        help_text='invoice pk that response associated with')
    is_fraud = models.BooleanField(
        default=False, db_index=True,
        help_text='Denotes whether the payment is fraud or not.')
    is_flagged = models.BooleanField(
        default=False, db_index=True,
        help_text='Denotes whether the payment is marked as flagged '
                  'or not.')
    is_flagged_email_sent = models.BooleanField(
        default=False, db_index=True,
        help_text='Denotes whether the flagged payment email was sent or not')
    card_bin = models.CharField(
        max_length=CARD_BIN_MAX_LENGTH, null=True, blank=True,
        db_index=True, help_text=
        'Denotes the bin number of the card used for the payment')
    card_last4 = models.CharField(max_length=4, null=True, blank=True,
                                  db_index=True,
                                  help_text=
                                  'Denotes the last 4 digits of the card'
                                  ' used for the payment')
    payment_method = models.CharField(max_length=200,
                                      choices=PAYMENT_METHOD_CHOICES,
                                      default=PAYMENT_METHOD_CARD,
                                      db_index=True,
                                      help_text='Payment Method')
    payment_scheme = models.CharField(
        max_length=200,
        choices=PAYMENT_SCHEME_CHOICES,
        default=PAYMENT_SCHEME_NONE,
        db_index=True,
        help_text='Denotes the payment scheme used for the payment')
    card_issuer_country = models.CharField(
        max_length=4, null=True, blank=True, db_index=True,
        help_text=' Denotes two letter code card issued country.')
    payment_id = models.CharField(
        max_length=200, null=True, blank=True,
        help_text='Payment id received from checkout.com')
    financial_action_response_data = models.JSONField(
        null=True, blank=True, help_text='Response data received after '
                                         'calling financial-actions api.')
    gateway_fee_authorization = models.DecimalField(
        decimal_places=8, max_digits=12, null=True, blank=True,
        help_text="Used to store gateway authorization fee from financial "
                  "action data")
    gateway_fee_void = models.DecimalField(
        decimal_places=8, max_digits=12, null=True, blank=True,
        help_text="Used to store gateway void fee from financial "
                  "action data")
    gateway_fee_refund = models.DecimalField(
        decimal_places=8, max_digits=12, null=True, blank=True,
        help_text="Used to store gateway refund fee from financial "
                  "action data")
    blended_variable_fee = models.DecimalField(
        decimal_places=8, max_digits=12, null=True, blank=True,
        help_text="Used to store blended variable fee from financial "
                  "action data")
    gateway_fee_authorization_vat = models.DecimalField(
        decimal_places=8, max_digits=12, null=True, blank=True,
        help_text="Used to store gateway authorization fee vat from financial"
                  " action data")
    gateway_fee_void_vat = models.DecimalField(
        decimal_places=8, max_digits=12, null=True, blank=True,
        help_text="Used to store gateway void fee vat from financial "
                  "action data")
    gateway_fee_refund_vat = models.DecimalField(
        decimal_places=8, max_digits=12, null=True, blank=True,
        help_text="Used to store gateway refund fee vat from financial "
                  "action data")
    blended_variable_fee_vat = models.DecimalField(
        decimal_places=8, max_digits=12, null=True, blank=True,
        help_text="Used to store blended variable fee vat from financial "
                  "action data")
    card_category = models.CharField(
        max_length=20, null=True, blank=True,
        help_text='Denotes the card category i.e. consumer/commercial')
    entity_id = models.CharField(
        max_length=40, null=True, blank=True,
        help_text='The unique id related to the merchant account')
    issuer_bank = models.CharField(
        max_length=200, null=True, blank=True,
        help_text='Denotes the card issued bank.'
    )
    cvv_check = models.CharField(
        max_length=10, null=True, blank=True,
        help_text='cvv check info.'
    )
    three_ds_check = models.BooleanField(default=False, null=True, blank=True)
    card_type = models.CharField(
        max_length=20, null=True, blank=True,
        help_text='Card type info from checkout.com'
    )
    checkout_response_code = models.CharField(
        max_length=50, null=True, blank=True,
        help_text='response code from checkoutpg'
    )
    is_gcc_card = models.BooleanField(default=False, null=True, blank=True)


@receiver(post_save, sender=TransactionData)
def calculate_checkout_gateway_charge(sender, instance, created, **kwargs):
    try:
        logger.info(
            "checkoutpg gateway charge calculating signal executing for"
            " {}".format(instance.payment_reference))

        if instance.financial_action_response_data:
            financial_kwargs = {
                "pk": instance.id,
                "financial_action_data": instance.financial_action_response_data,
                "model_name": MODEL_NAME_TRANSACTIONDATA
            }
            common_update_financial_action_charges.delay(**financial_kwargs)
    except Exception as e:
        logger.error(
            "Exception on calculate_checkout_gateway_charge for "
            "payment reference {}, error :{}".format(
                instance.payment_reference, str(e)), exc_info=True)


@receiver(post_save, sender=TransactionData)
def youpay_transaction_data_post_save_on_webhook(sender, instance, created,
                                                 **kwargs):
    payment_reference = None
    transaction_id = None
    is_success, is_youpay_updated = False, False

    try:
        financial_action_data = instance.financial_action_response_data
        if financial_action_data:
            """
            Blocking youpay update if financial action data is present and
            status is not in ALLOWED_STATUS_FOR_YOUPAY_WEBHOOK_UPDATE
            """
            status = instance.status
            if status not in ALLOWED_STATUS_FOR_YOUPAY_WEBHOOK_UPDATE:
                logger.info(
                    "Checkoutpg TransactionData post_save Not Triggered for "
                    "reference {}, status {}".format(
                        instance.payment_reference,
                        instance.status))
                return
            else:
                logger.info(
                    "Checkoutpg TransactionData post_save Triggering for "
                    "reference {}, status {}".format(
                        instance.payment_reference,
                        instance.status))

        payment_reference = instance.payment_reference

        data_to_update = prepare_youpay_transaction_update_data(
            instance, payment_reference)

        if data_to_update:
            transaction_id = data_to_update.get('transaction_id')
            from integrations.v1.gateway_clients.checkoutpg import (
                CheckoutpgManager)

            checkout_obj = CheckoutpgManager()
            is_youpay_updated = checkout_obj.update_youpay_transaction_data(
                data_to_update)
            is_success = True
    except Exception as e:
        logger.error(
            "Exception : Checkoutpg TransactionData post_save for "
            "payment reference {}, error :{}".format(
                payment_reference, str(e)), exc_info=True)
        is_success = False
    finally:
        logger.info(
            "Checkoutpg TransactionData post_save Triggered for tid {}, "
            "reference {}, is_completed {}, youpay updated {}".format(
                transaction_id, payment_reference, is_success,
                is_youpay_updated))


def prepare_youpay_transaction_update_data(instance, payment_reference):

    from core.utils import checkout_decline_check
    from services.v1.views.common import YouPayTransactionCRUD

    payment_status, is_payment_verified = checkout_decline_check(
        {'response_code': instance.checkout_response_code,
         'status': instance.status})
    youpay_obj = YouPayTransactionCRUD()

    try:
        transaction_obj = (
            youpay_obj.get_youpay_transaction_data_with_payment_reference(
                payment_reference))
        if transaction_obj:
            data_to_update = {
                'transaction_id': transaction_obj.transaction_id,
                "payment_status": (
                    payment_status.lower() if payment_status else None),
                "payment_reference": instance.payment_reference,
                "response_summary": instance.response_summary,
                "card_bin": instance.card_bin,
                "card_last4": instance.card_last4,
                'payment_scheme': instance.payment_scheme,
                'card_issuer_country': instance.card_issuer_country,
                'gateway_charge': 0,
                "approved": instance.approved,
                'is_gcc_card': instance.is_gcc_card,
                'is_fraud': instance.is_fraud,
                'is_flagged': instance.is_flagged,
            }
            if is_rewards_order_reference(transaction_obj.order_reference):
                existing_udf1 = getattr(transaction_obj, "udf1", {}) or {}
                existing_udf1.update({
                    'auth_code': instance.auth_code,
                    'is_notification': instance.is_notification,
                    'idempotency_key': instance.idempotency_key
                })
                data_to_update["udf1"] = existing_udf1
            # Update udf1, additional fee details if payment_scheme is Amex
            if (instance.payment_scheme == PAYMENT_SCHEME_AMERICAN_EXPRESS
                    and "amex_fee_config" not in (
                            data_to_update.get("udf1") or getattr(
                        transaction_obj, "udf1", {}) or {})
                    and instance.status == PAYMENT_STATUS_PAID
            ):
                logger.info(
                    "Payment scheme is Amex, calculating additional fee for"
                    " reference {}".format(instance.payment_reference))
                additional_fee_obj = get_gateway_additional_fee(
                    transaction_obj.currency, ADDITIONAL_AMEX_CARD_FEE,
                    CHECKOUTPG_HUB_CODE, "checkout_card")
                additional_fee_config = (
                    get_checkout_amex_additional_fee(
                        additional_fee_obj, transaction_obj))
                data_to_update[
                    "additional_total_amount"] = additional_fee_config.get(
                    "total_amount")
                data_to_update[
                    "additional_processing_fee"] = additional_fee_config.get(
                    "additional_fee")
                data_to_update[
                    "additional_processing_fee_vat"] = additional_fee_config.get(
                    "additional_fee_vat")
                existing_udf1 = data_to_update.get("udf1") or getattr(
                    transaction_obj, "udf1", {}) or {}
                existing_udf1.update({
                    'amex_fee_config': additional_fee_config
                })
                data_to_update["udf1"] = existing_udf1
            return data_to_update
        else:
            logger.info(
                "Transaction object not found for payment reference "
                "{}".format(payment_reference))
            return None
    except Exception as e:
        logger.error("Error while preparing data for youpay transaction "
                     "update {}".format(e), exc_info=True)

