def get_data_from_request(fields, request_data):
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
