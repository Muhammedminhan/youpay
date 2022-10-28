import datetime


# generate a random string with datetime
def random_string():
    return str(datetime.datetime.now().strftime("%H%M00%d%m%Y"))


invoice = random_string()
TABBY_CREATE_SESSION_SAMPLE_BODY = {
    "amount": 50.0,
    "currency": "AED",
    "language": "en",
    "platform": "Android",
    "cancel_url": "https://emapi.yougotagift.com/api/v6/payment/tabby/response/cancel/Android/",
    "invoice_id": invoice,
    "failure_url": "https://emapi.yougotagift.com/api/v6/payment/tabby/response/failure/Android/",
    "order_items": [
        {
            "title": "Centrepoint",
            "category": "Gift Card",
            "reference_id": "11509661"
        }
    ],
    "success_url": "https://emapi.yougotagift.com/api/v6/payment/tabby/response/Android/",
    "customer_name": "test",
    "loyalty_level": 0,
    "order_history": [],
    "customer_email": "otp.success@tabby.ai",
    "customer_phone": None,
    "order_reference": "TEST-1071340|ygag|25DM6XSSVP",
    "registered_since": "2022-09-19T15:54:46Z",
    "payment_reference": "SAMPLE-Invoice-" + invoice + "|ygag|25DM6XSSVP",
    "customer_ip_address": "83.110.91.86"
}
