from unittest.mock import Mock

from django.test import RequestFactory, TestCase

from core.middleware.client_ip import ClientIPMiddleware


class ClientIPMiddlewareTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.get_response = Mock()
        self.middleware = ClientIPMiddleware(self.get_response)

    def test_x_forwarded_for(self):
        request = self.factory.get(
            "/",
            HTTP_X_FORWARDED_FOR="203.0.113.1, 203.0.113.2",
        )
        self.middleware(request)
        self.assertEqual(request.client_ip, "203.0.113.1")

    def test_remote_addr_fallback(self):
        request = self.factory.get("/")
        request.META["REMOTE_ADDR"] = "198.51.100.1"
        self.middleware(request)
        self.assertEqual(request.client_ip, "198.51.100.1")
