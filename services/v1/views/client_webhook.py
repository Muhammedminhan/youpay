import datetime
import logging

import requests

from core.constants import EXTERNAL_API_REQUEST_TIMEOUT
from core.exceptions import ClientWebhookException
from core.utils import retry

logger = logging.getLogger(__name__)


class ClientService(object):
    """
    This is used to send webhook to client
    """

    def webhook_service(self, ygpay_transaction):
        from payments.serializers.ygpay_payments import (
            YGPayTransactionDataSerializer
        )

        if ygpay_transaction:
            try:
                serializer = YGPayTransactionDataSerializer(ygpay_transaction)
                request_data_json = serializer.data
                url = ygpay_transaction.api_client.endpoint_url
                headers = {
                    'Accept': 'application/json',
                    'date': str(datetime.datetime.utcnow()),
                }
                logger.info("Request data: {}".format(request_data_json))
                response_status = self.sent_webhook_to_client(
                    url,
                    request_data_json,
                    headers)

                if response_status is True:
                    logger.info(
                        "successfully post webhook to client status is"
                        " {}".format(response_status))
                else:
                    logger.error("post webhook to client status is {}".format(
                        response_status))
            except Exception as e:
                logger.error("Error sending webhook to client {}".format(
                    str(e)))

        else:
            logger.error("Unable to find the transaction")

    @retry(ClientWebhookException, tries=3, logger=logger)
    def sent_webhook_to_client(self, url, request_data_json, headers):
        logger.info("Sending webhooks to {} started".format(url))
        try:
            response = requests.post(url, json=request_data_json,
                                     headers=headers,
                                     timeout=EXTERNAL_API_REQUEST_TIMEOUT)
            if response:
                response_data = response.json()
                if response_data:
                    response_status = response_data.get('data').get('status')
                    if response_status is False:
                        logger.error(
                            "webhook failed : {}".format(
                                response_data))
                        raise ClientWebhookException("webhook Fail")
                    else:
                        logger.info("webhook sent successfully")
                        return True
                else:
                    logger.error("webhook failed : {}"
                                 .format(response_data))
                    raise ClientWebhookException(
                        "webhook failed : No response is received")
            else:
                error_message = "Webhook failed {} for {}".format(
                    url, request_data_json
                )
                raise ClientWebhookException(error_message)

        except Exception as e:
            raise ClientWebhookException("Webhook Failed: {}".format(str(e)))
