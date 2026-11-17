import os
import unittest
from unittest.mock import patch

import httpx
import jwt
from scalekit.common.scalekit import TokenValidationOptions

import main
from auth import ScalekitTokenVerifier, create_mcp_auth
from config import Settings, load_settings


class FakeScalekitClient:
    def __init__(self, claims: dict[str, object] | None = None) -> None:
        self.claims = claims or {
            "client_id": "mcp-client",
            "sub": "radio-user",
            "scope": "radio:read",
            "exp": 2_000_000_000,
        }
        self.validation_options: TokenValidationOptions | None = None

    def validate_token(
        self,
        token: str,
        *,
        options: TokenValidationOptions,
    ) -> dict[str, object]:
        self.validation_options = options
        if token == "invalid":
            raise jwt.InvalidTokenError("invalid token")
        return self.claims


class ConfigTests(unittest.TestCase):
    def test_loads_settings_and_rejects_wildcard_origins(self) -> None:
        env = {
            "SCALEKIT_ENVIRONMENT_URL": "https://example.scalekit.com/",
            "SCALEKIT_CLIENT_ID": "client-id",
            "SCALEKIT_CLIENT_SECRET": "client-secret",
            "SCALEKIT_RESOURCE_ID": "res_radio",
            "SCALEKIT_AUDIENCE_NAME": "radio-api",
            "SCALEKIT_RESOURCE_METADATA_URL": "https://radio.example.com/radio/mcp",
            "CORS_ALLOW_ORIGINS": "https://radio.example.com, http://localhost:3000",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = load_settings()

        self.assertEqual(
            settings.scalekit_environment_url,
            "https://example.scalekit.com",
        )
        self.assertEqual(
            settings.cors_allow_origins,
            ("https://radio.example.com", "http://localhost:3000"),
        )
        self.assertEqual(
            settings.resource_server_url,
            "https://radio.example.com/radio/mcp",
        )

        with patch.dict(
            os.environ,
            {**env, "CORS_ALLOW_ORIGINS": "*"},
            clear=True,
        ):
            with self.assertRaisesRegex(ValueError, "explicit origins"):
                load_settings()


class ScalekitTokenVerifierTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.settings = Settings(
            scalekit_environment_url="https://example.scalekit.com",
            scalekit_client_id="client-id",
            scalekit_client_secret="client-secret",
            scalekit_resource_id="res_radio",
            scalekit_audience_name="radio-api",
            resource_server_url="http://127.0.0.1:10000/radio/mcp",
            cors_allow_origins=("http://localhost:3000",),
        )

    async def test_validates_issuer_and_audience(self) -> None:
        client = FakeScalekitClient()
        auth_settings, verifier = create_mcp_auth(self.settings, client=client)

        access_token = await verifier.verify_token("valid")

        self.assertIsNotNone(access_token)
        assert access_token is not None
        self.assertEqual(access_token.client_id, "mcp-client")
        self.assertEqual(access_token.subject, "radio-user")
        self.assertEqual(access_token.scopes, ["radio:read"])
        self.assertIsNotNone(client.validation_options)
        assert client.validation_options is not None
        self.assertEqual(
            client.validation_options.issuer,
            "https://example.scalekit.com/resources/res_radio",
        )
        self.assertEqual(client.validation_options.audience, ["radio-api"])
        self.assertEqual(
            str(auth_settings.issuer_url),
            "https://example.scalekit.com/resources/res_radio",
        )
        self.assertFalse(auth_settings.validate_token_resource)

    async def test_invalid_token_is_rejected(self) -> None:
        verifier = ScalekitTokenVerifier(
            FakeScalekitClient(),
            TokenValidationOptions(
                issuer="https://example.scalekit.com/resources/res_radio",
                audience=["radio-api"],
            ),
        )

        self.assertIsNone(await verifier.verify_token("invalid"))


class AuthenticatedMcpAppTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        settings = Settings(
            scalekit_environment_url="https://example.scalekit.com",
            scalekit_client_id="client-id",
            scalekit_client_secret="client-secret",
            scalekit_resource_id="res_radio",
            scalekit_audience_name="radio-api",
            resource_server_url="http://127.0.0.1:10000/radio/mcp",
            cors_allow_origins=("http://localhost:3000",),
        )
        self.app = main.create_app(settings, scalekit_client=FakeScalekitClient())
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.app),
            base_url="http://127.0.0.1:10000",
        )

    async def asyncTearDown(self) -> None:
        await self.client.aclose()

    async def test_missing_bearer_token_returns_401_with_oauth_challenge(self) -> None:
        response = await self.client.get(
            "/radio/mcp",
            headers={"host": "127.0.0.1:10000"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertIn("WWW-Authenticate", response.headers)
        self.assertIn("oauth-protected-resource", response.headers["WWW-Authenticate"])

    async def test_configured_public_host_is_allowed(self) -> None:
        settings = Settings(
            scalekit_environment_url="https://example.scalekit.com",
            scalekit_client_id="client-id",
            scalekit_client_secret="client-secret",
            scalekit_resource_id="res_radio",
            scalekit_audience_name="radio-api",
            resource_server_url="https://mcp-server-radio.onrender.com/radio/mcp",
            cors_allow_origins=("http://localhost:3000",),
        )
        app = main.create_app(settings, scalekit_client=FakeScalekitClient())
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="https://mcp-server-radio.onrender.com",
        ) as client:
            response = await client.get(
                "/radio/mcp",
                headers={"host": "mcp-server-radio.onrender.com"},
            )

        self.assertEqual(response.status_code, 401)

    async def test_cors_preflight_allows_configured_origin_and_methods(self) -> None:
        response = await self.client.options(
            "/radio/mcp",
            headers={
                "host": "127.0.0.1:10000",
                "origin": "http://localhost:3000",
                "access-control-request-method": "POST",
                "access-control-request-headers": "authorization,content-type",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["access-control-allow-origin"],
            "http://localhost:3000",
        )
        self.assertEqual(response.headers["access-control-allow-credentials"], "true")
        self.assertIn("DELETE", response.headers["access-control-allow-methods"])

    async def test_valid_bearer_token_passes_authentication_middleware(self) -> None:
        response = await self.client.get(
            "/radio/mcp",
            headers={
                "host": "127.0.0.1:10000",
                "authorization": "Bearer valid",
            },
        )

        self.assertNotEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
