TOKEN_TYPE_SAVED_CARD = 'savedcard'
TOKEN_TYPE_CARD = 'card'
TOKEN_TYPE_PAYPAL = 'paypal'
RESPONSE_CODE_LIST = [
    '20005',  # Declined - Do not honour
    '20014',  # Invalid card number
    '012',  # Invalid payment
    '029',
    '050',
    '079',
    '084',
    '034',
    '20151',  # Declined - Payment authorization initiated but failed
    None
]
YOUPAY_SESSION_KEY = "youpay-session-id"
