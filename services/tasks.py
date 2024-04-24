import logging
from datetime import datetime

from celery import shared_task

from integrations.constants import CHECKOUTPG_HUB_CODE, B2CPAYBACK_HUB_CODE
from integrations.v1.gateway_clients.b2c_payback import B2CPaybackManager
from integrations.v1.gateway_clients.checkoutpg import CheckoutpgManager
from services.models import ConfigurationData

logger = logging.getLogger(__name__)


@shared_task(name='get_configuration_data')
def get_configuration_data(payment_gateway=None, currency=None):
    """
    Task to get the latest configuration data from different payment gateways.

    Args:
        payment_gateway (str): The code of the payment gateway.
        currency (str): The ISO code of the currency.

    Returns:
        None
    """
    logger.info(
        "Getting latest configuration data for {}".format(payment_gateway))
    configuration_data = ConfigurationData.objects.all()

    if payment_gateway:
        configuration_data = configuration_data.filter(
            payment_gateway__code=payment_gateway)
    if currency:
        configuration_data = configuration_data.filter(
            currency__iso_code=currency)

    update_data = {}

    for item in configuration_data:
        if item.payment_gateway.code == CHECKOUTPG_HUB_CODE:
            response = get_checkout_conf(item.currency.iso_code)
        elif item.payment_gateway__code == B2CPAYBACK_HUB_CODE:
            response = get_b2c_conf(item.currency.iso_code)
        else:
            response = None

        if response:
            update_data[item.id] = response

    for item_id, response_data in update_data.items():
        ConfigurationData.objects.filter(id=item_id).update(
            response_data=response_data, updated_at=datetime.now())


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
    return b2c_config
