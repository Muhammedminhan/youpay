class ClientWebhookException(Exception):
    """
    ClientWebhookException
    client webhooks exceptions
    """
    pass


class WaitLockException(Exception):
    """
    WaitLockException
    If retry limit exceeds the maximum limit
    """
    pass


class ValidationFailed(Exception):
    """Exception to be raised when validation fails."""
    pass


class TransactionNotFoundException(Exception):
    """Exception to be raised when transaction not found."""
    pass


class TransactionAlreadyPaidException(Exception):
    """Exception to be raised when transaction already processed."""
    pass


class TransactionAlreadyCancelledException(Exception):
    """Exception to be raised when transaction already processed."""
    pass
