import random
import string


def unique_token_generator(size=10, is_upper=True):
    """
    :param size: size of the string
    :param is_upper: specify string letter in upper or lowe case
    :return: random unique string token
    """
    if is_upper:
        string_ascii = string.ascii_uppercase
    else:
        string_ascii = string.ascii_lowercase
    unique_code = ''.join(
        random.SystemRandom().choice(
            # translate removes the characters from string
            string_ascii.translate('IJO') +
            string.digits.translate('01')
        ) for _ in range(size))
    return unique_code


def _get_payment_reference_number(order_reference):
    """
    Create a payment reference number for all the future Checkout
    communications. This will be created using uuid and the given order
    reference number.
    :param order_reference:
    :return:
    """
    reference_number = '%s|%s' % (order_reference,
                                       unique_token_generator())
    return reference_number
