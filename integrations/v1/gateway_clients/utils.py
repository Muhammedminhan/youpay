from payments.models import YouPayTransactionData


def get_transaction_object(self, transaction_id):
    """
    Method for retrieve transaction object
    """
    transaction_object = YouPayTransactionData.objects.get(
        transaction_id=transaction_id)
    return transaction_object


def update_transaction_object(self):
    pass
