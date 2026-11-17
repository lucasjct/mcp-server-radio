# Radio Browser MCP server

An MCP server for searching the Radio Browser directory of internet radio
stations. It serves MCP over Streamable HTTP at
`http://127.0.0.1:10000/radio/mcp`.

## Run in VS Code

Open this project folder in VS Code with `uv` installed. The workspace server
is configured in `.vscode/mcp.json`; use the Start button shown above that file
or run **MCP: List Servers** from the Command Palette.

To start it manually:

```sh
cp .env.example .env
# Fill in the Scalekit values in .env
uv run main.py
```

Keep the process running while connected. The server needs network access when
a search is made.

## OAuth authentication

The Streamable HTTP endpoint requires a Scalekit-issued OAuth 2.0 bearer token.
Create an MCP server in the Scalekit dashboard, enable Dynamic Client
Registration and Client ID Metadata Documents for compatible MCP hosts, then
copy its environment URL, client credentials, resource ID, and audience name into `.env`.
Scalekit handles the interactive login and authorization flow; the MCP server
validates each access token's signature, issuer, expiration, and resource
audience name before serving tools.

Set `SCALEKIT_RESOURCE_METADA_URL` to the externally reachable MCP endpoint
when deploying behind a proxy. Set `CORS_ALLOW_ORIGINS` to a comma-separated
list of exact browser origins. Origins are explicit because credentials are
enabled; wildcard origins are rejected. The default list allows common local
development origins.

Never commit `.env` or put real credentials in `.env.example`.

## Tools

- `search_radio_stations` searches by any combination of station name, country,
  two-letter country code, language, and tag.
- `search_radio` searches by station name. Exact matching is enabled by default.
- `search_radio_by_country` searches using an ISO 3166-1 alpha-2 country code.
- `search_radio_by_language` searches by language.

Each search returns up to 50 stations, ordered by vote count, and includes
stream URLs and useful station metadata. Broken stations are excluded. Searches
are read-only and do not start streams or increment station click counters.

## References

- [VS Code MCP developer guide](https://code.visualstudio.com/api/extension-guides/ai/mcp.md)
- [Radio Browser API](https://www.radio-browser.info/). 


### Inspect the MCP

Run `npx @modelcontextprotocol/inspector` and connect to
`http://127.0.0.1:10000/radio/mcp` using Streamable HTTP.

### MCP server configuration

VS Code reads the server configuration from `.vscode/mcp.json`. It uses the
same Streamable HTTP URL above. Configure the Scalekit MCP server as the OAuth
authorization server for that resource so VS Code can complete login and send
its bearer token.
### Examples to ask

*"using mcp-server-radio (confirm it), give the name of the top 5 US radios.  Give me the link of these radios"*.  

*"List to me the top five radios from Brasil"*.   
