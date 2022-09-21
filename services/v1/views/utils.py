from integrations.constants import (
    CHECKOUTPG_HUB_CODE, B2CPAYBACK_HUB_CODE, TABBYPG_HUB_CODE
)
from payments.constants import PAYMENT_STATUS_INITIATED
from services.v1.constants import PAYMENT_GATEWAYS


def reformat_payment_request_data(data):
    """
    used to reformat payment request data
    """

    data['amount'] = data['order']['amount']
    data['invoice_id'] = data['payment']['invoice_id']
    data['currency'] = data['order']['currency']
    data['order_reference'] = data['payment']['order_reference']
    data['customer_email'] = data['customer']['email']
    data['customer_phone'] = data['customer']['phone']
    data['language'] = data['payment']['language']
    data['platform'] = data['payment']['payment_platform']
    data['ip'] = data['payment']['ip']
    data['service_fee'] = data['order']['service_fee']
    data['base_amount'] = data['order']['base_amount']
    data['VAT_amount'] = data['order']['VAT_amount']
    data['payment_status'] = PAYMENT_STATUS_INITIATED

    return data


def get_data_from_request(fields, request_data):
    """
    used to get data from request
    """
    data = {}
    for field in fields:
        data[field] = request_data.get(field)
    data['request_data'] = request_data
    return data


def get_session_id_and_transaction_id(id):
    """
    used to get session_id and transaction_id from id
    syntax : "session_id-transaction_id"
    example : "SESSION_ID-5717e1f3-727d-4bc5-8055-b65ea096b422"
    """
    session_id = id.split('-')[0]
    transaction_id = id.split('-')[1:]
    delimiter = '-'
    return session_id, delimiter.join(transaction_id)


def get_gateways(payment_gateway_serializer):
    """
    used to get gateways from payment gateway serializer
    """
    response_payment_gateways = PAYMENT_GATEWAYS

    payment_gateways = payment_gateway_serializer.data

    for payment_gateway in payment_gateways:
        code = payment_gateway.get('code')
        if code == CHECKOUTPG_HUB_CODE:
            response_payment_gateways['checkoutpg'] = True
            response_payment_gateways['saved_card'] = True
            response_payment_gateways['applepay'] = True

        if code == B2CPAYBACK_HUB_CODE:
            response_payment_gateways['adcb'] = True

        if code == TABBYPG_HUB_CODE:
            response_payment_gateways['tabbypg'] = True

    return response_payment_gateways
