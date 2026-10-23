# Radio Browser and Movie MCP servers

This project contains two MCP servers exposed over HTTP: one for searching the
Radio Browser station directory and one for searching local IMDb datasets with
Cinemagoer.

## Run the radio server

With [uv](https://docs.astral.sh/uv/) installed, run:

```bash
uv run main.py
```

The combined server listens at `http://127.0.0.1:10000`. Keep it running while
connected, and use **MCP: List Servers** in VS Code to manage the endpoints
configured in `.vscode/mcp.json`. The radio endpoint is
`http://127.0.0.1:10000/radio/mcp`; the movie endpoint is
`http://127.0.0.1:10000/movie/mcp`. Radio searches need network access.

## Tools

- `search_radio_stations` searches by any combination of station name, country,
  two-letter country code, language, and tag.
- `search_radio` searches by station name. Exact matching is enabled by default.
- `search_radio_by_country` searches using an ISO 3166-1 alpha-2 country code.
- `search_radio_by_language` searches by language.

Each search returns up to 50 stations, ordered by vote count, and includes
stream URLs and useful station metadata. Broken stations are excluded. Searches
are read-only and do not start streams or increment station click counters.

## Movie database MCP server

`movies_mcp.py` provides the movie tools served by the combined HTTP app.
Cinemagoer works with a local database imported from IMDb's freely downloadable
datasets; it does not scrape IMDb pages or provide a live IMDb web API.

Download the IMDb TSV datasets you need from
[datasets.imdbws.com](https://datasets.imdbws.com/) and import them with
Cinemagoer's `s32cinemagoer.py` utility:

```sh
uv run s32cinemagoer.py /path/to/imdb-tsv-files/ sqlite:///cinemagoer.db
```

Set `CINEMAGOER_DB_URI` to the populated database path before starting the
combined server, for example:

```sh
CINEMAGOER_DB_URI="sqlite:////absolute/path/to/cinemagoer.db" uv run main.py
}
```

The tools are `search_movies`, `get_movie_details`, and
`get_top_rated_movies`. The top-rated tool returns feature films ordered by
IMDb average rating, with a default minimum of 10,000 votes; you can set a
different `min_votes` threshold. All tools are read-only, validate their
inputs, and return structured movie metadata. The default database URI is
`sqlite:///cinemagoer.db` relative to the server's working directory; set
`CINEMAGOER_DB_URI` when your imported dataset is stored elsewhere. An empty
or unimported database is not usable and produces a clear tool error.

## References

- [VS Code MCP developer guide](https://code.visualstudio.com/api/extension-guides/ai/mcp.md)
- [Radio Browser API](https://www.radio-browser.info/)
- [Cinemagoer](https://github.com/cinemagoer/cinemagoer)
- [MCP server development guide](https://github.com/cyanheads/model-context-protocol-resources/blob/main/guides/mcp-server-development-guide.md)


Inspect either endpoint with `npx @modelcontextprotocol/inspector`, selecting
its URL from above.

## Example prompts

- “Using mcp-server-radio, list the top 5 radio stations in the US and their
  stream links.”
- “Using mcp-server-movies, search for The Matrix and show its details.”  
- "Recommend a good movie rated 8 on IMDb for me to watch today."  
