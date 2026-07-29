import hashlib
import hmac
import json
import time
import logging

from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated

logger = logging.getLogger(__name__)


class HMACAuthentication(BaseAuthentication):
    """
    Common hmac authentication for all payment gateway clients
    """
    MAX_TIME_DIFF = 5 * 60

    def authenticate_header(self, request):
        return "HMAC"

    def get_secret(self, request):
        view = request.parser_context["view"]
        secret_provider = getattr(view, "hmac_secret", None)

        if callable(secret_provider):
            return secret_provider(request)

        if secret_provider:
            return secret_provider

        return settings.APPLEPAY_HMAC_SECRET

    def authenticate(self, request):
        timestamp = request.headers.get("X-Timestamp")
        signature = request.headers.get("X-Signature")

        if not timestamp or not signature:
            raise NotAuthenticated()

        self.validate_timestamp(timestamp)

        canonical = self.build_canonical_request(
            request=request,
            timestamp=timestamp,
        )

        expected_signature = self.sign(canonical, request)

        if not hmac.compare_digest(expected_signature, signature):
            raise AuthenticationFailed()

        return (None, None)

    def build_canonical_request(self, request, timestamp):
        """
        Creates the canonical request string.

        METHOD
        PATH
        QUERY
        BODY
        TIMESTAMP
        """

        query_string = request.META.get("QUERY_STRING", "")

        body = self.get_request_body(request)

        return "".join([
            request.path,
            query_string,
            body,
            timestamp,
        ])

    def get_request_body(self, request):
        """
        Returns request body as deterministic JSON.
        """

        if request.method in ("GET", "DELETE"):
            return ""

        if not request.body:
            return ""

        try:
            body = json.loads(request.body.decode())

            return json.dumps(
                body,
                separators=(",", ":"),
                sort_keys=True,
            )

        except Exception:
            return request.body.decode(errors="replace")

    def sign(self, canonical_request, request):
        """
        Creates HMAC SHA256 signature.
        """
        secret = self.get_secret(request)
        return hmac.new(
            secret.encode(),
            canonical_request.encode(),
            hashlib.sha256,
        ).hexdigest()

    def validate_timestamp(self, timestamp):
        """
        Reject requests older than 5 minutes.
        """

        try:
            timestamp = int(timestamp)
        except ValueError:
            raise AuthenticationFailed("Invalid timestamp")

        current_time = int(time.time())

        if abs(current_time - timestamp) > self.MAX_TIME_DIFF:
            raise AuthenticationFailed("Request expired")
