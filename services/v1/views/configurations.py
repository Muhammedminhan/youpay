import logging

from rest_framework.viewsets import ViewSet

logger = logging.getLogger(__name__)


class ConfigView(ViewSet):

    def list(self, request):
        # TODO
        #  - get uuid from the request
        #  - identify the transaction object
        #  - identify the client(product)
        #  - identify the available payment options for the product
        #  - prepare config response
        pass
