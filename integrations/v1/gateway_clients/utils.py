import logging

from payments.models import YouPayTransactionData

logger = logging.getLogger(__name__)


def get_saved_fields(saved_fields, data_dict, payment_transaction):
    for key, value in data_dict.items():
        if value:
            payment_transaction.__dict__[key] = value
            saved_fields.append(key)

    return saved_fields


def get_transaction_object(transaction_id):
    """
    Method for retrieve transaction object
    """
    transaction_object = YouPayTransactionData.objects.get(
        transaction_id=transaction_id)
    return transaction_object


def update_transaction_object(data):
    data_dict = {}
    transaction_id = data.get('id', None)
    data_dict['approved'] = data.get('approved', None)
    try:
        payment_transaction = get_transaction_object(
            transaction_id)
        saved_fields = ['api_response_data', 'modified_on']
        if payment_transaction:
            saved_fields = get_saved_fields(saved_fields,
                                            data_dict,
                                            payment_transaction)
            payment_transaction.save(update_fields=saved_fields)

    except Exception as e:
        logger.error(
            "while update youpa transaction got exception {0}".format(
                str(e)))
