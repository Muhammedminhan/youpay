import datetime
import json
import logging

import requests

from core.constants import EXTERNAL_API_REQUEST_TIMEOUT
from core.exceptions import ClientWebhookException
from core.utils import retry

logger = logging.getLogger(__name__)


class ClientService(object):

    def webhook_service(self, ygpay_transaction):
        response_status = False

        if ygpay_transaction:
            try:
                url = ygpay_transaction.get("api_client_url")
                headers = {
                    'Accept': 'application/json',
                    'date': str(datetime.datetime.utcnow()),
                }
                request_data_json = json.dumps(ygpay_transaction)
                logger.info("Request data: {}".format(request_data_json))
                response_status = self.sent_webhook_to_client(url,
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
                        raise ClientWebhookException("webhook Fail")
                    else:
                        return True
            else:
                return False
        except Exception as e:
            raise ClientWebhookException("Webhook Failed: {}".format(str(e)))
