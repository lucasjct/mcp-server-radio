import os
from dataclasses import dataclass
from urllib.parse import urlsplit

from dotenv import load_dotenv

_DEFAULT_RESOURCE_SERVER_URL = "http://127.0.0.1:10000/radio/mcp"
_DEFAULT_CORS_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)


@dataclass(frozen=True)
class Settings:
    scalekit_environment_url: str
    scalekit_client_id: str
    scalekit_client_secret: str
    scalekit_resource_id: str
    scalekit_audience_name: str
    resource_server_url: str
    cors_allow_origins: tuple[str, ...]


def _validate_url(name: str, value: str, *, https_only: bool = False) -> str:
    parsed = urlsplit(value)
    if not parsed.hostname or parsed.scheme not in ({"https"} if https_only else {"http", "https"}):
        requirement = "an HTTPS URL" if https_only else "an HTTP(S) URL"
        raise ValueError(f"{name} must be {requirement}")
    return value.rstrip("/")


def load_settings() -> Settings:
    load_dotenv()

    required = {
        "SCALEKIT_ENVIRONMENT_URL": os.getenv("SCALEKIT_ENVIRONMENT_URL"),
        "SCALEKIT_CLIENT_ID": os.getenv("SCALEKIT_CLIENT_ID"),
        "SCALEKIT_CLIENT_SECRET": os.getenv("SCALEKIT_CLIENT_SECRET"),
        "SCALEKIT_RESOURCE_ID": os.getenv("SCALEKIT_RESOURCE_ID"),
        "SCALEKIT_AUDIENCE_NAME": os.getenv("SCALEKIT_AUDIENCE_NAME"),
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    origins = tuple(
        origin.strip()
        for origin in os.getenv("CORS_ALLOW_ORIGINS", ",".join(_DEFAULT_CORS_ORIGINS)).split(",")
        if origin.strip()
    )
    if not origins or "*" in origins:
        raise ValueError("CORS_ALLOW_ORIGINS must contain explicit origins when credentials are enabled")
    for origin in origins:
        parsed_origin = urlsplit(origin)
        if (
            parsed_origin.scheme not in {"http", "https"}
            or not parsed_origin.hostname
            or parsed_origin.path not in ("", "/")
            or parsed_origin.query
            or parsed_origin.fragment
        ):
            raise ValueError(f"Invalid CORS origin: {origin}")

    environment_url = _validate_url(
        "SCALEKIT_ENVIRONMENT_URL",
        required["SCALEKIT_ENVIRONMENT_URL"],
        https_only=True,
    )
    resource_server_url = _validate_url(
        "SCALEKIT_RESOURCE_METADATA_URL",
        os.getenv("SCALEKIT_RESOURCE_METADATA_URL", _DEFAULT_RESOURCE_SERVER_URL),
    )

    return Settings(
        scalekit_environment_url=environment_url,
        scalekit_client_id=required["SCALEKIT_CLIENT_ID"],
        scalekit_client_secret=required["SCALEKIT_CLIENT_SECRET"],
        scalekit_resource_id=required["SCALEKIT_RESOURCE_ID"],
        scalekit_audience_name=required["SCALEKIT_AUDIENCE_NAME"],
        resource_server_url=resource_server_url,
        cors_allow_origins=origins,
    )
