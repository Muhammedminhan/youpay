def get_data_from_request(fields, request_data):
    data = {}
    for field in fields:
        data[field] = request_data.get(field)
    data['request_data'] = request_data
    return data
