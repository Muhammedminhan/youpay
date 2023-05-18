import logging

from django.contrib import messages

from payments.constants import ALLOW_ARCHIVE_STATUS_LIST
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
