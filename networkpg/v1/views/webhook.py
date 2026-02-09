import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from networkpg.services.webhook_service import WebhookService

logger = logging.getLogger(__name__)


class NetworkWebhookListener(APIView):
    """
    Endpoint to receive webhooks from Network International.
    """
    # permission_classes = []
    # authentication_classes = []
    def get(self, request, *args, **kwargs):
        logger.info(f"get Received Network Webhook: {request.data}")
        self.post(request, *args, **kwargs)
        return Response({"status": "received"}, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        logger.info(f"Received Network Webhook: {request.data}")
        
        # In a real scenario, verify signature here if provided
        
        success = WebhookService.process_event(request.data)
        
        if success:
            return Response({"status": "received"}, status=status.HTTP_200_OK)
        else:
            # We still return 200/202 to the gateway to stop retries if it's just a missing record
            return Response({"status": "recognized"}, status=status.HTTP_202_ACCEPTED)
