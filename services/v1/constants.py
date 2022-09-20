from integrations.constants import (
    CHECKOUTPG_HUB_CODE,
    B2CPAYBACK_HUB_CODE,
    TABBYPG_HUB_CODE, SAVEDCARD_HUB_CODE, APPLEPAY_HUB_CODE
)

PAYMENT_GATEWAYS = [
    {
        "gateway_name": "saved_card",
        "code": SAVEDCARD_HUB_CODE,
    },
    {
        "gateway_name": "checkoutpg",
        "code": CHECKOUTPG_HUB_CODE,
    },
    {
        "gateway_name": "adcb",
        "code": B2CPAYBACK_HUB_CODE,
    },
    {
        "gateway_name": "tabbypg",
        "code": TABBYPG_HUB_CODE,
    },
    {
        "gateway_name": "applepay",
        "code": APPLEPAY_HUB_CODE,
    },
]
