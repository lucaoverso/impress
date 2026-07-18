import importlib
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from security.rate_limit import InMemoryRateLimiter, rate_limiter


class RateLimiterTest(unittest.TestCase):
    def test_blocks_until_window_expires(self):
        now = [100.0]
        limiter = InMemoryRateLimiter(clock=lambda: now[0])
        rule = [("login:account", "professor@escola", 2, 60)]

        self.assertTrue(limiter.allow(rule))
        self.assertTrue(limiter.allow(rule))
        self.assertFalse(limiter.allow(rule))

        now[0] += 61
        self.assertTrue(limiter.allow(rule))


class RateLimitRouterTest(unittest.TestCase):
    def setUp(self):
        rate_limiter.clear()

    def tearDown(self):
        rate_limiter.clear()

    def test_login_returns_429_after_account_limit(self):
        auth = importlib.import_module("auth")
        app = FastAPI()
        app.include_router(auth.router)

        with (
            patch.object(auth, "autenticar_usuario", return_value=None),
            patch.object(auth, "record_event"),
            TestClient(app) as client,
        ):
            for _ in range(10):
                response = client.post(
                    "/login",
                    json={"email": "unknown@school.test", "senha": "invalid"},
                )
                self.assertEqual(response.status_code, 401)

            response = client.post(
                "/login",
                json={"email": "unknown@school.test", "senha": "invalid"},
            )
            self.assertEqual(response.status_code, 429)
            self.assertEqual(
                response.json()["detail"],
                "Muitas tentativas. Tente novamente mais tarde.",
            )


if __name__ == "__main__":
    unittest.main()
