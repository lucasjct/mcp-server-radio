import os
import re
import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

from imdb import Cinemagoer, IMDbBase, IMDbDataAccessError
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations
from pydantic import Field
from sqlalchemy.engine import make_url


movie_server = MCPServer(
    "cinemagoer",
    title="Cinemagoer",
    instructions=(
        "Search and retrieve movie information from a local database imported "
        "from IMDb's freely downloadable datasets. This server does not scrape "
        "IMDb pages or access a remote IMDb API."
    ),
)

_TOOL_ANNOTATIONS = ToolAnnotations(readOnlyHint=True, openWorldHint=False)
_DEFAULT_DATABASE_URI = "sqlite:///cinemagoer.db"
_MAX_RESULTS = 50


@lru_cache(maxsize=1)
def _get_cinemagoer(database_uri: str) -> IMDbBase:
    _validate_database(database_uri)
    return Cinemagoer("s3", uri=database_uri)


def _sqlite_database_path(database_uri: str) -> Path | None:
    database_url = make_url(database_uri)
    if database_url.get_backend_name() != "sqlite" or database_url.database == ":memory:":
        return None
    return Path(database_url.database or "").resolve()


def _validate_database(database_uri: str) -> None:
    database_path = _sqlite_database_path(database_uri)
    if database_path is None:
        return
    if not database_path.is_file():
        raise ToolError(
            f"IMDb dataset database not found at '{database_path}'. "
            "Import the IMDb TSV datasets with Cinemagoer's s32cinemagoer.py."
        )

    try:
        with sqlite3.connect(database_path.as_uri() + "?mode=ro", uri=True) as connection:
            has_title_basics = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
                ("title_basics",),
            ).fetchone()
    except sqlite3.Error as exc:
        raise ToolError(
            f"Could not open IMDb dataset database at '{database_path}': {exc}"
        ) from exc

    if has_title_basics is None:
        raise ToolError(
            f"IMDb dataset database at '{database_path}' is empty or not imported. "
            "Import the IMDb TSV datasets with Cinemagoer's s32cinemagoer.py."
        )


def _database_uri() -> str:
    return os.environ.get("CINEMAGOER_DB_URI", _DEFAULT_DATABASE_URI)


def _validate_limit(limit: int) -> None:
    if isinstance(limit, bool) or not 1 <= limit <= _MAX_RESULTS:
        raise ToolError(f"limit must be between 1 and {_MAX_RESULTS}")


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value if item is not None and str(item)]
    return []


def _format_movie_summary(movie: Any) -> dict[str, Any]:
    return {
        "imdb_id": str(getattr(movie, "movieID", "")),
        "title": movie.get("title"),
        "year": movie.get("year"),
        "kind": movie.get("kind"),
        "genres": _string_list(movie.get("genres")),
    }


def _validate_min_votes(min_votes: int) -> None:
    if isinstance(min_votes, bool) or not isinstance(min_votes, int) or min_votes < 0:
        raise ToolError("min_votes must be a non-negative integer")


@movie_server.tool(
    title="Search movies",
    description=(
        "Search the configured local IMDb dataset by movie title. Returns up to "
        "50 matching movies with IMDb ID, title, year, type, and genres."
    ),
    annotations=_TOOL_ANNOTATIONS,
)
def search_movies(
    query: Annotated[str, Field(description="Movie title or title fragment to search for.")],
    limit: Annotated[
        int, Field(ge=1, le=50, description="Maximum number of results (1-50).")
    ] = 10,
) -> list[dict[str, Any]]:
    _validate_limit(limit)
    normalized_query = query.strip()
    if not normalized_query:
        raise ToolError("query must not be empty")

    try:
        movies = _get_cinemagoer(_database_uri()).search_movie(
            normalized_query,
            results=limit,
        )
    except IMDbDataAccessError as exc:
        raise ToolError(
            "Cinemagoer could not read the IMDb database. Set CINEMAGOER_DB_URI "
            "to a populated database imported from the IMDb datasets."
        ) from exc

    return [_format_movie_summary(movie) for movie in movies]


@movie_server.tool(
    title="List top-rated movies",
    description=(
        "List feature films from the configured local IMDb dataset ordered by "
        "IMDb average rating, highest first. The default minimum of 10,000 votes "
        "helps avoid titles with very few ratings dominating the results."
    ),
    annotations=_TOOL_ANNOTATIONS,
)
def get_top_rated_movies(
    limit: Annotated[
        int, Field(ge=1, le=50, description="Maximum number of movies to return (1-50).")
    ] = 10,
    min_votes: Annotated[
        int, Field(ge=0, description="Only include movies with at least this many IMDb votes.")
    ] = 10_000,
) -> list[dict[str, Any]]:
    _validate_limit(limit)
    _validate_min_votes(min_votes)

    database_uri = _database_uri()
    database_path = _sqlite_database_path(database_uri)
    if database_path is None:
        raise ToolError("get_top_rated_movies requires a file-backed SQLite IMDb database")
    _validate_database(database_uri)

    try:
        with sqlite3.connect(database_path.as_uri() + "?mode=ro", uri=True) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT
                    b.tconst AS imdb_id,
                    b.primaryTitle AS title,
                    b.startYear AS year,
                    b.genres AS genres,
                    r.averageRating AS rating,
                    r.numVotes AS vote_count
                FROM title_basics AS b
                JOIN title_ratings AS r ON r.tconst = b.tconst
                WHERE b.titleType = 'movie'
                    AND b.isAdult = 0
                    AND r.numVotes >= ?
                ORDER BY r.averageRating DESC, r.numVotes DESC, b.primaryTitle ASC
                LIMIT ?
                """,
                (min_votes, limit),
            ).fetchall()
    except sqlite3.Error as exc:
        raise ToolError(
            "Could not query IMDb ratings. Ensure the imported dataset contains "
            "the title_ratings table."
        ) from exc

    return [
        {
            "imdb_id": f"tt{str(row['imdb_id']).zfill(7)}",
            "title": row["title"],
            "year": row["year"],
            "genres": [genre.lower() for genre in (row["genres"] or "").split(",") if genre],
            "rating": row["rating"],
            "vote_count": row["vote_count"],
        }
        for row in rows
    ]


@movie_server.tool(
    title="Get movie details",
    description=(
        "Get title, year, type, genres, runtime, rating, vote count, and plot "
        "from the configured local IMDb dataset using a numeric IMDb ID."
    ),
    annotations=_TOOL_ANNOTATIONS,
)
def get_movie_details(
    imdb_id: Annotated[
        str, Field(description="Numeric IMDb title ID, with or without the 'tt' prefix.")
    ],
) -> dict[str, Any]:
    normalized_id = imdb_id.strip()
    if normalized_id.startswith("tt"):
        normalized_id = normalized_id[2:]
    if not re.fullmatch(r"\d{1,12}", normalized_id):
        raise ToolError(
            "imdb_id must be a numeric IMDb title ID, optionally prefixed with 'tt'. "
            "To look up a title, call search_movies first and pass its imdb_id result."
        )

    try:
        movie = _get_cinemagoer(_database_uri()).get_movie(
            normalized_id,
            info=["main", "plot"],
        )
    except IMDbDataAccessError as exc:
        raise ToolError(
            "Cinemagoer could not read the IMDb database. Set CINEMAGOER_DB_URI "
            "to a populated database imported from the IMDb datasets."
        ) from exc

    if not movie.get("title"):
        raise ToolError(f"No movie with IMDb ID tt{normalized_id} was found")

    result = _format_movie_summary(movie)
    result.update(
        {
            "runtime_minutes": _string_list(movie.get("runtimes")),
            "rating": movie.get("rating"),
            "vote_count": movie.get("votes"),
            "plot": _string_list(movie.get("plot")),
        }
    )
    return result


def main() -> None:
    movie_server.run("streamable-http")


if __name__ == "__main__":
    main()