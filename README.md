# Radio Browser MCP server

An MCP server for searching the Radio Browser directory of internet radio
stations. It exposes the MCP Streamable HTTP transport at
`http://127.0.0.1:8000/mcp`.

## Run the HTTP server

Install [uv](https://docs.astral.sh/uv/) if needed, then start the server from
the project directory:

```bash
uv run main.py
```

Keep this terminal open while using the MCP server. It is a long-running HTTP
service, and its request logs (for example, `INFO: ... POST /mcp ...`) are
normal. Stop it with `Ctrl+C`. The server needs network access when a station
search is made.

## Connect an MCP client

Add the following server entry to an MCP client's configuration. For clients
that use the `mcpServers` configuration format, use this snippet:

```json
{
    "mcpServers": {
        "mcp-radio-http": {
            "type": "http",
            "url": "http://127.0.0.1:8000/mcp",
            "tools": [
                "*"
            ]
        }
    }
}
```

Start the HTTP server before connecting the client. If you restart the server,
reconnect the MCP client so it can establish a new session. The URL must point
to `/mcp`; requests to the server root (`/`) are not the MCP endpoint.

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
- [Radio Browser API](https://www.radio-browser.info/)

To inspect the MCP server, run `npx @modelcontextprotocol/inspector` and
connect it to `http://127.0.0.1:8000/mcp`.

## Example prompts

- “Using mcp-radio-http, give me the top 5 radio stations in the US and their
  stream links.”
- “List the top five radio stations in Brazil.”
