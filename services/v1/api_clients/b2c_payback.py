import logging

from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response

from services.v1.views.common import YouPayTransactionCRUD
from core.response_messages import YouPayResponse

from integrations.v1.gateway_clients.b2c_payback import B2CPaybackManager

logger = logging.getLogger(__name__)


class B2CPaybackPointBalance(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        payback = B2CPaybackManager()
        response = payback.get_point_balance()
        # TODO
        #  - create payment request data
        #  -update transaction table with status, payment method, etc
        #  - handle payment response
        return Response(response, status=status.HTTP_200_OK)


class B2CPaybackAuthenticate(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        payback = B2CPaybackManager()
        response = payback.authenticate_redemption()
        # TODO
        #  - create payment request data
        #  -update transaction table with status, payment method, etc
        #  - handle payment response
        return Response(response, status=status.HTTP_200_OK)