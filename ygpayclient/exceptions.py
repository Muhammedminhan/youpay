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
