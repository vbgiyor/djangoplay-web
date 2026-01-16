from django.middleware.csrf import get_token
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


@extend_schema(exclude=True, tags=["Authentication: CSRF"])
class CSRFTokenView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Obtain CSRF Token",
        responses={
            200: OpenApiResponse(
                response={"csrfToken": {"type": "string"}}
            )
        },
    )
    def get(self, request):
        return Response(
            {"csrfToken": get_token(request)},
            status=status.HTTP_200_OK,
        )
