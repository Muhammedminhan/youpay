from payments.constants import PAYMENT_STATUS_INITIATED


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
