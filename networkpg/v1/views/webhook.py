import logging
from networkpg.constants import NI_WEBHOOK_SECRET
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from networkpg.services.webhook_service import WebhookService

logger = logging.getLogger(__name__)


class NetworkWebhookListener(APIView):
    """
    Endpoint to receive webhooks from Network International.
    """

    def post(self, request, *args, **kwargs):
        signature = request.headers.get('X-NI-Signature')
        if not signature or signature != NI_WEBHOOK_SECRET:
            logger.warning(
                f"Unauthorized Webhook Access Attempt. Header: {signature}")
            return Response(
                {"status": "unauthorized"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        logger.info(f"Received Network Webhook: {request.data}")

        success = WebhookService.process_event(request.data)

        if success:
            return Response({"status": "received"}, status=status.HTTP_200_OK)
        else:
            return Response({"status": "recognized"}, status=status.HTTP_202_ACCEPTED)
