import asyncio
from typing import Any, Protocol

import jwt
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from scalekit import ScalekitClient
from scalekit.common.scalekit import TokenValidationOptions

from config import Settings


class TokenValidationClient(Protocol):
    def validate_token(
        self,
        token: str,
        *,
        options: TokenValidationOptions,
    ) -> dict[str, Any]: ...


class ScalekitTokenVerifier:
    def __init__(
        self,
        client: TokenValidationClient,
        validation_options: TokenValidationOptions,
    ) -> None:
        self._client = client
        self._validation_options = validation_options

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            claims = await asyncio.to_thread(
                self._client.validate_token,
                token,
                options=self._validation_options,
            )
        except (jwt.InvalidTokenError, KeyError):
            return None

        client_id = claims.get("client_id") or claims.get("azp")
        expires_at = claims.get("exp")
        if (
            not isinstance(client_id, str)
            or not client_id
            or isinstance(expires_at, bool)
            or not isinstance(expires_at, (int, float))
        ):
            return None

        raw_scopes = claims.get("scope", "")
        if isinstance(raw_scopes, str):
            scopes = raw_scopes.split()
        elif isinstance(raw_scopes, list) and all(isinstance(scope, str) for scope in raw_scopes):
            scopes = raw_scopes
        else:
            return None

        subject = claims.get("sub")
        if subject is not None and not isinstance(subject, str):
            return None

        return AccessToken(
            token=token,
            client_id=client_id,
            scopes=scopes,
            expires_at=int(expires_at),
            subject=subject,
            claims=claims,
        )


def create_mcp_auth(
    settings: Settings,
    *,
    client: TokenValidationClient | None = None,
) -> tuple[AuthSettings, ScalekitTokenVerifier]:
    scalekit_client = client or ScalekitClient(
        env_url=settings.scalekit_environment_url,
        client_id=settings.scalekit_client_id,
        client_secret=settings.scalekit_client_secret,
    )
    issuer_url = (
        f"{settings.scalekit_environment_url}/resources/{settings.scalekit_resource_id}"
    )
    validation_options = TokenValidationOptions(
        issuer=issuer_url,
        audience=[settings.scalekit_audience_name],
    )
    auth_settings = AuthSettings(
        issuer_url=issuer_url,
        resource_server_url=settings.resource_server_url,
        validate_token_resource=False,
    )
    return auth_settings, ScalekitTokenVerifier(scalekit_client, validation_options)
