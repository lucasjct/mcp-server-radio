# Radio Browser MCP Server

A Model Context Protocol (MCP) server that lets MCP clients search the Radio
Browser directory for internet radio stations. It exposes read-only search
tools over Streamable HTTP and protects the endpoint with OAuth 2.0 bearer
tokens issued by Scalekit.

## Features

- Search stations by name, country, country code, language, and tag.
- Find stations by country code or broadcast language.
- Return station stream URLs and metadata, ordered by vote count.
- Authenticate MCP requests with Scalekit-issued access tokens.

## Requirements

- Python 3.11 or later
- [uv](https://docs.astral.sh/uv/)
- A Scalekit environment and MCP resource configured for OAuth

## Configuration

Create a `.env` file in the project root and provide the following settings:

| Variable | Required | Description |
| --- | --- | --- |
| `SCALEKIT_ENVIRONMENT_URL` | Yes | HTTPS URL of your Scalekit environment. |
| `SCALEKIT_CLIENT_ID` | Yes | Scalekit client ID used by this resource server. |
| `SCALEKIT_CLIENT_SECRET` | Yes | Secret for the Scalekit client. Keep it private. |
| `SCALEKIT_RESOURCE_ID` | Yes | ID of the MCP resource configured in Scalekit. |
| `SCALEKIT_AUDIENCE_NAME` | Yes | Audience value expected in access tokens. |
| `SCALEKIT_RESOURCE_METADATA_URL` | For deployment | Public MCP endpoint URL, such as `https://your-service.onrender.com/radio/mcp`. |
| `CORS_ALLOW_ORIGINS` | No | Comma-separated list of exact browser origins. Defaults to common local development origins. |
| `PORT` | No | Listening port provided by the hosting platform. Defaults to `10000`. |

`SCALEKIT_AUDIENCE_NAME`, `SCALEKIT_RESOURCE_ID`, and
`SCALEKIT_RESOURCE_METADATA_URL` serve different purposes; use the values
configured for their corresponding fields in Scalekit. The metadata URL should
be the public MCP endpoint, including `/radio/mcp`. The server constructs the
OAuth protected-resource metadata URL from it.

Never commit `.env` or expose real credentials in examples, logs, or support
requests.

## Run locally

Install dependencies and start the server:

```sh
uv sync
uv run main.py
```

The local Streamable HTTP endpoint is:

```text
http://127.0.0.1:10000/radio/mcp
```

Keep the server running while using it. Station searches require outbound
network access to the Radio Browser API.

## Connect an MCP client

For VS Code, the workspace configuration is in `.vscode/mcp.json`. It points
to the local endpoint by default. To connect to a deployed server, configure
the MCP client with the deployed endpoint, for example:

```json
{
  "servers": {
    "radio-browser": {
      "type": "http",
      "url": "https://your-service.onrender.com/radio/mcp"
    }
  }
}
```

Complete the OAuth sign-in when prompted by the client. The client must send a
valid Scalekit bearer token to use the tools.

## Deploy to Render

Create a Render **Web Service** for this repository and use the start command:

```sh
uv run main.py
```

Set the required Scalekit variables in the Render dashboard. Set
`SCALEKIT_RESOURCE_METADATA_URL` to the public endpoint URL, such as
`https://your-service.onrender.com/radio/mcp`, and configure the corresponding
resource and audience in Scalekit. Render supplies `PORT`; the server binds to
that port and listens on `0.0.0.0`.

The root URL (`https://your-service.onrender.com/`) is not an application page
and may return `404 Not Found`. Use `/radio/mcp` as the MCP endpoint. An
unauthenticated request to that endpoint may return `401 Authentication
required`; an MCP client should follow the OAuth flow.

## Available tools

| Tool | Purpose |
| --- | --- |
| `search_radio_stations` | Search by any combination of station name, country, two-letter country code, language, and tag. |
| `search_radio` | Search by station name, with exact matching enabled by default. |
| `search_radio_by_country` | Search by ISO 3166-1 alpha-2 country code. |
| `search_radio_by_language` | Search by broadcast language. |

Searches return up to 50 stations, ordered by Radio Browser votes, with stream
URLs and station metadata. Broken stations are excluded. Searches are
read-only: they do not start streams or increment station click counters.

## Troubleshooting

- **Root URL returns 404:** This is expected. Connect to `/radio/mcp`.
- **MCP endpoint returns 401:** Authenticate through the MCP client's OAuth
  flow. Confirm the client is using the correct Scalekit environment, resource,
  and audience.
- **Render reports no open port:** Confirm the service is a Web Service, the
  start command is `uv run main.py`, and the startup logs show Uvicorn listening
  on `0.0.0.0` and Render's `PORT`.
- **Requests time out:** Check Render logs and outbound connectivity to the
  Radio Browser API. A sleeping instance may also take time to wake.

## Inspect the server

Run the MCP Inspector and connect it to the local Streamable HTTP endpoint:

```sh
npx @modelcontextprotocol/inspector
```

## References

- [VS Code MCP developer guide](https://code.visualstudio.com/api/extension-guides/ai/mcp.md)
- [Radio Browser](https://www.radio-browser.info/)
- [Scalekit MCP authentication](https://docs.scalekit.com/authenticate/mcp/)
