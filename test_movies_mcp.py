import os
import sqlite3
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import movies_mcp
from imdb import IMDbDataAccessError
from mcp.server.mcpserver.exceptions import ToolError


class FakeMovie(dict):
    movieID = "0133093"


class FakeCinemagoer:
    def __init__(self) -> None:
        self.search_arguments: tuple[str, int] | None = None
        self.get_arguments: tuple[str, list[str]] | None = None

    def search_movie(self, query: str, results: int) -> list[FakeMovie]:
        self.search_arguments = (query, results)
        return [
            FakeMovie(
                title="The Matrix",
                year=1999,
                kind="movie",
                genres=["Action", "Sci-Fi"],
            )
        ]

    def get_movie(self, imdb_id: str, info: list[str]) -> FakeMovie:
        self.get_arguments = (imdb_id, info)
        return FakeMovie(
            title="The Matrix",
            year=1999,
            kind="movie",
            genres=["Action", "Sci-Fi"],
            runtimes=["136"],
            rating=8.7,
            votes=2_000_000,
            plot=["A computer hacker learns about the true nature of reality."],
        )


class MovieToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cinemagoer = FakeCinemagoer()
        self.client_patch = patch(
            "movies_mcp._get_cinemagoer",
            return_value=self.cinemagoer,
        )
        self.client_patch.start()
        self.addCleanup(self.client_patch.stop)

    def test_search_movies_trims_query_and_formats_summaries(self) -> None:
        movies = movies_mcp.search_movies("  The Matrix  ", limit=3)

        self.assertEqual(self.cinemagoer.search_arguments, ("The Matrix", 3))
        self.assertEqual(
            movies,
            [
                {
                    "imdb_id": "0133093",
                    "title": "The Matrix",
                    "year": 1999,
                    "kind": "movie",
                    "genres": ["Action", "Sci-Fi"],
                }
            ],
        )

    def test_get_movie_details_accepts_tt_prefix_and_returns_metadata(self) -> None:
        movie = movies_mcp.get_movie_details("tt0133093")

        self.assertEqual(self.cinemagoer.get_arguments, ("0133093", ["main", "plot"]))
        self.assertEqual(movie["title"], "The Matrix")
        self.assertEqual(movie["runtime_minutes"], ["136"])
        self.assertEqual(movie["plot"], ["A computer hacker learns about the true nature of reality."])

    def test_validates_query_limit_and_imdb_id(self) -> None:
        with self.assertRaisesRegex(ToolError, "query must not be empty"):
            movies_mcp.search_movies("   ")

        with self.assertRaisesRegex(ToolError, "between 1 and 50"):
            movies_mcp.search_movies("Matrix", limit=51)

        with self.assertRaisesRegex(ToolError, "numeric IMDb title ID"):
            movies_mcp.get_movie_details("not-an-id")

    def test_reports_unavailable_dataset_as_tool_error(self) -> None:
        with patch(
            "movies_mcp._get_cinemagoer",
            side_effect=IMDbDataAccessError("missing title_basics table"),
        ):
            with self.assertRaisesRegex(ToolError, "populated database"):
                movies_mcp.search_movies("The Matrix")

    def test_rejects_empty_sqlite_database_before_opening_cinemagoer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            original_directory = Path.cwd()
            os.chdir(directory)
            Path("empty.db").touch()
            self.client_patch.stop()
            movies_mcp._get_cinemagoer.cache_clear()
            try:
                with (
                    patch.dict(os.environ, {"CINEMAGOER_DB_URI": "sqlite:///empty.db"}),
                    patch("movies_mcp.Cinemagoer") as cinemagoer_factory,
                ):
                    with self.assertRaisesRegex(ToolError, "empty or not imported"):
                        movies_mcp.search_movies("The Matrix")

                cinemagoer_factory.assert_not_called()
            finally:
                os.chdir(original_directory)
                movies_mcp._get_cinemagoer.cache_clear()

    def test_lists_top_rated_movies_with_vote_and_adult_filters(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "imdb.db"
            with sqlite3.connect(database_path) as connection:
                connection.executescript(
                    """
                    CREATE TABLE title_basics (
                        tconst INTEGER,
                        titleType TEXT,
                        primaryTitle TEXT,
                        startYear INTEGER,
                        isAdult INTEGER,
                        genres TEXT
                    );
                    CREATE TABLE title_ratings (
                        tconst INTEGER,
                        averageRating REAL,
                        numVotes INTEGER
                    );
                    INSERT INTO title_basics VALUES
                        (111, 'movie', 'High Score', 2020, 0, 'Drama,Sci-Fi'),
                        (222, 'movie', 'Low Votes', 2021, 0, 'Comedy'),
                        (333, 'movie', 'Adult Film', 2022, 1, 'Drama'),
                        (444, 'movie', 'Second Place', 2019, 0, 'Action');
                    INSERT INTO title_ratings VALUES
                        (111, 9.5, 20000),
                        (222, 10.0, 5),
                        (333, 10.0, 30000),
                        (444, 8.0, 15000);
                    """
                )

            database_uri = f"sqlite:///{database_path.as_posix()}"
            with patch.dict(os.environ, {"CINEMAGOER_DB_URI": database_uri}):
                results = movies_mcp.get_top_rated_movies(limit=5)

            self.assertEqual(
                results,
                [
                    {
                        "imdb_id": "tt0000111",
                        "title": "High Score",
                        "year": 2020,
                        "genres": ["drama", "sci-fi"],
                        "rating": 9.5,
                        "vote_count": 20000,
                    },
                    {
                        "imdb_id": "tt0000444",
                        "title": "Second Place",
                        "year": 2019,
                        "genres": ["action"],
                        "rating": 8.0,
                        "vote_count": 15000,
                    },
                ],
            )

    def test_validates_top_rated_movie_options(self) -> None:
        with self.assertRaisesRegex(ToolError, "between 1 and 50"):
            movies_mcp.get_top_rated_movies(limit=0)

        with self.assertRaisesRegex(ToolError, "non-negative"):
            movies_mcp.get_top_rated_movies(min_votes=-1)


if __name__ == "__main__":
    unittest.main()
