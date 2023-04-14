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


class TransactionNotFound(Exception):
    """Exception to be raised when transaction not found."""
    pass


class TransactionAlreadyPaid(Exception):
    """Exception to be raised when transaction already processed."""
    pass


class TransactionAlreadyCancelled(Exception):
    """Exception to be raised when transaction already processed."""
    pass
