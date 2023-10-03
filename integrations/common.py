class WebhookDataFormat(object):

    def get_issuer_bank(self, response_data):
        issuer_bank = response_data.get("source", {}).get("issuer")
        return issuer_bank

    def get_three_ds(self, response_data):
        three_ds = response_data.get("3ds", {}).get("challenged")
        return three_ds

    def get_cvv_check(self, response_data):
        cvv_check = response_data.get("source", {}).get("cvv_check")
        return cvv_check

    def get_card_type(self, response_data):
        card_type = response_data.get("source", {}).get("card_type")
        return card_type
