# TODO
#  - get checkoutpg configurations

from integrations.constants import CHECKOUTPG_PAYMENT_CONFIGURATIONS


class CheckoutpgManager(object):

    def get_configuratoins(self, currency):
        """
        Method for getting canfigurations
        """
        channel_code = CHECKOUTPG_PAYMENT_CONFIGURATIONS.get(
            currency.upper())

        # TODO - get checkoutpg from table

        # PARAMS = {'key': settings.CHECKOUTPG_API_KEY,
        #           'channel_code': channel_code}
        # URL = settings.CHECKOUTPG_DOMAIN + CHECKOUTPG_CONFIG_ENDPOINT
        #
        # response = requests.get(url=URL, params=PARAMS)


        #https: // checkoutpg - sandbox.yougotagift.com / gateway / checkout / api / v1 / configuration /?key = Xl72ODoOHJ0cVUmzY3ghB - u3rqxleSY1h47eDa527tc & channel_code = YGAGAE
        pass

    def get_saved_cards(self):
        """
        Method for getting saved cards
        """
        # https: // checkoutpg - sandbox.yougotagift.com / gateway / checkout / api / v1 / paymenttoken /?key = Cd0ZOH9uzeoeiysbsKWpluzvj3dwP0C_TmC_CZvbfIM & email = christi @ yougotagift.com
        pass
