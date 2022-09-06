from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.response_messages import YGPayResponse
from integrations.v1.gateway_clients.checkoutpg import CheckoutpgManager
from services.v1.constants import CHECKOUTPG_CARD_KEYWORDS, \
    CHECKOUTPG_LIST_CARD


class CheckoutpgCommunicationView(APIView):
    """API endpoint that allows users to be viewed or edited."""
    checkoutpg_obj = CheckoutpgManager()

    response_obj = YGPayResponse()

    def command(self, request, keyword):
        if keyword == CHECKOUTPG_LIST_CARD:
            return self.checkoutpg_obj.get_configuratoins(currency="AED")
        else:
            return self.response_obj.get_400_message(
                message="Invalid keyword")

    def get(self, request, keyword):
        try:
            if keyword not in CHECKOUTPG_CARD_KEYWORDS:
                data = self.response_obj.get_400_message(
                    message="Invalid keyword")
                return Response(data.get('errors'),
                                status=status.HTTP_400_BAD_REQUEST)
            else:
                api_response = self.command(request, keyword)
                data = self.response_obj.get_success_dict(
                    code=YGPayResponse.SUCCESS,
                    success_dict={'data': api_response})

                return Response(data, status=status.HTTP_200_OK)

        except Exception as e:
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)
