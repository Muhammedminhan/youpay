import logging

from celery import shared_task
from django.db.models import Q

from integrations.constants import CHECKOUTPG_HUB_CODE, B2CPAYBACK_HUB_CODE
from integrations.v1.gateway_clients.b2c_payback import B2CPaybackManager
from integrations.v1.gateway_clients.checkoutpg import CheckoutpgManager
from services.models import ConfigurationData

logger = logging.getLogger(__name__)


@shared_task(name='sync_configuration_data')
def sync_configuration_data(payment_gateway=None, currency=None):
    """
    Task to sync the latest configuration data from different payment gateways.

    Args:
        payment_gateway (str): The code of the payment gateway.
        currency (str): The ISO code of the currency.

    Returns:
        None
    """
    logger.info(
        "Getting latest configuration data for {}".format(payment_gateway))

    filters = Q()
    if payment_gateway:
        filters &= Q(payment_gateway__code=payment_gateway)
    if currency:
        filters &= Q(currency__iso_code=currency)

    configuration_data = ConfigurationData.objects.filter(filters)

    for item in configuration_data:
        response = None
        if item.payment_gateway.code == CHECKOUTPG_HUB_CODE:
            response = get_checkout_conf(item.currency.iso_code)
        elif item.payment_gateway.code == B2CPAYBACK_HUB_CODE:
            response = get_b2c_conf(item.currency.iso_code)

        if response:
            logger.info(
                "updating latest configuration data for {} , in {}".format(
                    payment_gateway, item))
            item.response_data = response
            item.save(update_fields=["response_data", "updated_at"])
            logger.info(
                "updated latest configuration data for {} , in {}".format(
                    payment_gateway, item))


def get_checkout_conf(currency):
    """
    Get Checkoutpg configurations.

    Args:
        currency (str): The ISO code of the currency.

    Returns:
        dict: Configuration data for Checkoutpg.
    """
    checkout_obj = CheckoutpgManager()
    checkout_config, status_code = checkout_obj.get_configurations(currency)

    logger.info(
        "Checkoutpg response: {}, {}".format(checkout_config, status_code))
    return checkout_config


def get_b2c_conf(currency):
    """
    Get B2CPayback configurations.

    Args:
        currency (str): The ISO code of the currency.

    Returns:
        dict: Configuration data for B2CPayback.
    """
    b2c_payback_obj = B2CPaybackManager()
    b2c_config = b2c_payback_obj.get_configurations(currency)
    logger.info("B2CPayback response: {}".format(b2c_config))
    return b2c_config
