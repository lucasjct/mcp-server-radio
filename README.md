# Radio Browser MCP server

An MCP server for searching the Radio Browser directory of internet radio
stations. It uses the local stdio transport supported by VS Code and the Python
MCP SDK.

## Run in VS Code

Open this project folder in VS Code with `uv` installed. The workspace server
is configured in `.vscode/mcp.json`; use the Start button shown above that file
or run **MCP: List Servers** from the Command Palette.

To start it manually:

```sh
uv run main.py
```

The server needs network access when a search is made. Its stdio output is
reserved for MCP protocol messages, so do not add `print`-based logging.

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


### To isnpect the MCP 

`npx @modelcontextprotocol/inspector` 

### MCP Server config. 
`.vscode/mcp.json`

```json
{
  "servers": {
     "mcp-server-radio": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/Users/<your-user>/<your-workspace>/mcp-server-radio",
        "main.py"
      ]
    }
  }
}
```
### Examples to ask

*"using mcp-server-radio (confirm it), give the name of the top 5 US radios.  Give me the link of these radios"*.  

*"List to me the top five radios from Brasil"*.   
