from decimal import Decimal


def get_decimal(request_data, key):
    return Decimal(
        request_data.get(key, None)) if request_data.get(key, None) else None
