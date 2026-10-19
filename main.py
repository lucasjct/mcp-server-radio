from functools import lru_cache
import re
from typing import Annotated, Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations
from pydantic import Field
from pyradios import RadioBrowser


server = MCPServer(
    "radio-browser",
    title="Radio Browser",
    instructions=(
        "Search the Radio Browser directory for internet radio stations. "
        "Search tools are read-only and return station stream URLs and metadata."
    ),
)

_TOOL_ANNOTATIONS = ToolAnnotations(readOnlyHint=True, openWorldHint=True)
_STATION_FIELDS = (
    "stationuuid",
    "name",
    "url",
    "url_resolved",
    "homepage",
    "favicon",
    "country",
    "countrycode",
    "state",
    "language",
    "tags",
    "codec",
    "bitrate",
    "votes",
    "clickcount",
    "lastcheckok",
)


@lru_cache(maxsize=1)
def _get_radio_browser() -> RadioBrowser:
    return RadioBrowser()


def _validate_limit(limit: int) -> None:
    if isinstance(limit, bool) or not 1 <= limit <= 50:
        raise ToolError("limit must be between 1 and 50")


def _format_station(station: dict[str, Any]) -> dict[str, str | int | bool | None]:
    return {field: station.get(field) for field in _STATION_FIELDS}


def _search_stations(
    *,
    limit: int = 10,
    **filters: str | bool,
) -> list[dict[str, str | int | bool | None]]:
    _validate_limit(limit)
    if not filters:
        raise ToolError("Provide at least one station search filter")

    stations = _get_radio_browser().search(
        **filters,
        limit=limit,
        hidebroken=True,
        order="votes",
        reverse=True,
    )
    return [_format_station(station) for station in stations]


@server.tool(
    title="Search radio stations",
    description=(
        "Search for internet radio stations by name, country, ISO 3166-1 alpha-2 "
        "country code, language, or tag. At least one filter is required. "
        "Returns up to 50 stations, ordered by votes, with stream URLs and metadata."
    ),
    annotations=_TOOL_ANNOTATIONS,
)
def search_radio_stations(
    name: Annotated[str | None, Field(description="Station name to search for.")] = None,
    country: Annotated[str | None, Field(description="Country name to search in.")] = None,
    country_code: Annotated[
        str | None, Field(description="Two-letter ISO 3166-1 alpha-2 country code.")
    ] = None,
    language: Annotated[str | None, Field(description="Broadcast language to search for.")] = None,
    tag: Annotated[str | None, Field(description="Station genre or tag to search for.")] = None,
    exact_name: Annotated[
        bool, Field(description="Require an exact station-name match when name is provided.")
    ] = False,
    limit: Annotated[
        int, Field(ge=1, le=50, description="Maximum results to return (1-50).")
    ] = 10,
) -> list[dict[str, str | int | bool | None]]:
    filters: dict[str, str | bool] = {}
    for value, parameter in (
        (name, "name"),
        (country, "country"),
        (language, "language"),
        (tag, "tag"),
    ):
        if value is not None:
            trimmed_value = value.strip()
            if not trimmed_value:
                raise ToolError(f"{parameter} must not be empty")
            filters[parameter] = trimmed_value

    if name is not None:
        filters["name_exact"] = exact_name

    if country_code is not None:
        normalized_code = country_code.strip().upper()
        if not re.fullmatch(r"[A-Z]{2}", normalized_code):
            raise ToolError("country_code must be a two-letter ISO 3166-1 code")
        filters["countrycode"] = normalized_code

    return _search_stations(limit=limit, **filters)


@server.tool(
    title="Search radio stations by name",
    description="Find radio stations by name and optionally require an exact name match.",
    annotations=_TOOL_ANNOTATIONS,
)
def search_radio(
    name: Annotated[str, Field(description="Station name to search for.")],
    exact_name: Annotated[
        bool, Field(description="Require an exact station-name match.")
    ] = True,
    limit: Annotated[
        int, Field(ge=1, le=50, description="Maximum results to return (1-50).")
    ] = 10,
) -> list[dict[str, str | int | bool | None]]:
    return search_radio_stations(name=name, exact_name=exact_name, limit=limit)


@server.tool(
    title="Search radio stations by country code",
    description="Find radio stations in a country using its two-letter ISO country code.",
    annotations=_TOOL_ANNOTATIONS,
)
def search_radio_by_country(
    countrycode: Annotated[
        str, Field(description="Two-letter ISO 3166-1 alpha-2 country code.")
    ],
    limit: Annotated[
        int, Field(ge=1, le=50, description="Maximum results to return (1-50).")
    ] = 10,
) -> list[dict[str, str | int | bool | None]]:
    return search_radio_stations(country_code=countrycode, limit=limit)


@server.tool(
    title="Search radio stations by language",
    description="Find radio stations that broadcast in the specified language.",
    annotations=_TOOL_ANNOTATIONS,
)
def search_radio_by_language(
    language: Annotated[str, Field(description="Broadcast language to search for.")],
    limit: Annotated[
        int, Field(ge=1, le=50, description="Maximum results to return (1-50).")
    ] = 10,
) -> list[dict[str, str | int | bool | None]]:
    return search_radio_stations(language=language, limit=limit)


def main() -> None:
    server.run("streamable-http")


if __name__ == "__main__":
    main()
