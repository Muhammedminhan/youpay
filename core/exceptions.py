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


class TransactionAlreadyExpired(Exception):
    """Exception to be raised when transaction already processed."""
    pass


class TransactionAlreadyVerified(Exception):
    """Exception to be raised when transaction already verified."""
    pass


class TransactionMaxAttemptReached(Exception):
    """Exception to be raised when transaction Max attempt reached."""
    pass


class ClientWebhookFailed(Exception):
    """Exception to be raised when validation fails."""
    pass
