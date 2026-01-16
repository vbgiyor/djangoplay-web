import logging

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


@extend_schema(exclude=True)
class AuthLogView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        event = request.data.get("event")
        user = request.data.get("user", "unknown")

        if event == "session_expired":
            logger.info(f"JWT session expired: {user}")
        elif event == "re_authenticated":
            logger.info(f"JWT re-authenticated: {user}")

        return Response({"status": "logged"}, status=200)
