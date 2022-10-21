# create session class here
from rest_framework.response import Response
from rest_framework.views import APIView

from services.v1.views.common import (
    YouPayTransactionCRUD, ClientValidator)


class CreateSession(YouPayTransactionCRUD, APIView, ClientValidator):
    def post(self, request):
        transaction_id = request.data.get('transaction_id')

        transaction_obj = self.get_youpay_transaction_data(transaction_id)

        payment_data = {
            'transaction_data': "transaction_data",
            'request_data': "request.data",
            'site_domain': "site_domain"}

        return Response({
            "data": payment_data,
        })
