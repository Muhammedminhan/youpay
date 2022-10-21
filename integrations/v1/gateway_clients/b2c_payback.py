from services.v1.views.payment import PaymentRequestView
from services.v1.views.payment_handlers import PaymentHandlers
from core.utils import get_b2cpayback_config


class B2CPaybackManager(PaymentRequestView, PaymentHandlers):
    """
    Class to manage b2cpayback related operations
    """

    def __init__(self):
        self.b2cpayback_config = get_b2cpayback_config()
