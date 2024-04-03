import logging

from django.contrib import messages

from core.response_messages import YouPayResponse
from integrations.v1.gateway_clients.neqaty_service import (
    NeqatyServiceManager)
from payments.constants import ALLOW_ARCHIVE_STATUS_LIST, PAYMENT_STATUS_PAID
from payments.models import (ArchivedYouPayTransactionData)

logger = logging.getLogger(__name__)


def archive_transaction_data(modeladmin, request, queryset):
    """
    Function to move YouPayTransactionData to ArchivedYouPayTransactionData
    """

    try:
        # prepared_data for bulk create, filtered_queryset for delete
        prepared_data, filtered_queryset = prepare_archive_transaction_objects(
            queryset)

        # Archiving Transactions
        is_archived = ArchivedYouPayTransactionData.objects.bulk_create(
            prepared_data)

        if len(is_archived):
            response_message = (
                "Archive worked for payment status having {} - Archived: {}, "
                "Deleted: {}, No Change:{}, Out of : {}".format(
                    (",".join(ALLOW_ARCHIVE_STATUS_LIST)),
                    len(prepared_data),
                    len(filtered_queryset),
                    (len(queryset) - len(prepared_data)),
                    len(queryset)
                ))

            logger.info(response_message)

            filtered_queryset.delete()

            modeladmin.message_user(request, response_message,
                                    level=messages.SUCCESS)
        else:
            modeladmin.message_user(request, "Nothing to archive",
                                    level=messages.WARNING)

    except Exception as e:
        response_message = "Archiving Failed : {}".format(
            str(e))
        logger.error(response_message)

        modeladmin.message_user(request, response_message,
                                level=messages.ERROR)


def prepare_archive_transaction_objects(youpaytransactiondata_queryset):
    """
    Function to process Archive YouPayTransactionData objects
    """

    filtered_queryset = (youpaytransactiondata_queryset.filter(
        payment_status__in=ALLOW_ARCHIVE_STATUS_LIST))

    dict_data = filtered_queryset.values()

    archive_transaction_objects = [ArchivedYouPayTransactionData(
        **item) for item in dict_data]

    return archive_transaction_objects, filtered_queryset


def collect_neqaty_points_for_transaction(modeladmin, request, queryset):
    try:
        if queryset.count() != 1:
            modeladmin.message_user(request,
                                    "You can only select one transaction to process.",
                                    level=messages.WARNING)
        transaction = queryset.first()

        if transaction.payment_status == PAYMENT_STATUS_PAID and (
                transaction.point_collection_enabled):
            neqaty_obj = NeqatyServiceManager()
            response, code = neqaty_obj.collect_points(transaction)
            response_obj = YouPayResponse()

            if code == response_obj.SUCCESS:
                response_message = (
                    "Neqaty collection successful for the transaction {}".format(
                        transaction.transaction_id
                    ))
                logger.info(response_message)
                modeladmin.message_user(request, response_message,
                                        level=messages.SUCCESS)
            else:
                response_message = (
                    "Neqaty collection failed for the transaction {}".format(
                        transaction.transaction_id
                    ))
                logger.info(response_message)
                modeladmin.message_user(request, response_message,
                                        level=messages.ERROR)
        else:
            response_message = (
                "Neqaty collection not available for this transaction {}".format(
                    transaction.transaction_id
                ))
            modeladmin.message_user(request, response_message,
                                    level=messages.ERROR)

    except Exception as e:
        response_message = ("Collecting points of neqaty failed with error : "
                            "{}".format(str(e)))
        logger.error(response_message)
        modeladmin.message_user(request, response_message,
                                level=messages.ERROR)
