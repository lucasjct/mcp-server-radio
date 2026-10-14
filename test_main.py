import unittest
from unittest.mock import patch

import main
from mcp.server.mcpserver.exceptions import ToolError


class FakeRadioBrowser:
    def __init__(self) -> None:
        self.search_arguments: dict[str, str | int | bool] | None = None

    def search(self, **kwargs: str | int | bool) -> list[dict[str, str | int | bool]]:
        self.search_arguments = kwargs
        return [
            {
                "stationuuid": "station-1",
                "name": "Example Jazz",
                "url": "http://stream.example/radio",
                "url_resolved": "http://stream.example/radio",
                "countrycode": "US",
                "votes": 12,
                "unrequested_field": "not returned",
            }
        ]


class RadioSearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.browser = FakeRadioBrowser()
        self.browser_patch = patch("main._get_radio_browser", return_value=self.browser)
        self.browser_patch.start()
        self.addCleanup(self.browser_patch.stop)

    def test_searches_with_multiple_filters_and_returns_station_metadata(self) -> None:
        stations = main.search_radio_stations(
            name="  Jazz ",
            country_code="us",
            exact_name=True,
            limit=5,
        )

        self.assertEqual(
            self.browser.search_arguments,
            {
                "name": "Jazz",
                "name_exact": True,
                "countrycode": "US",
                "limit": 5,
                "hidebroken": True,
                "order": "votes",
                "reverse": True,
            },
        )
        self.assertEqual(stations[0]["name"], "Example Jazz")
        self.assertEqual(stations[0]["url_resolved"], "http://stream.example/radio")
        self.assertNotIn("unrequested_field", stations[0])

    def test_legacy_search_tools_use_correct_radio_browser_filters(self) -> None:
        main.search_radio("BBC Radio 1")
        self.assertEqual(self.browser.search_arguments["name"], "BBC Radio 1")
        self.assertTrue(self.browser.search_arguments["name_exact"])

        main.search_radio_by_country("gb")
        self.assertEqual(self.browser.search_arguments["countrycode"], "GB")

        main.search_radio_by_language("English")
        self.assertEqual(self.browser.search_arguments["language"], "English")

    def test_requires_a_filter_and_valid_country_code(self) -> None:
        with self.assertRaisesRegex(ToolError, "at least one"):
            main.search_radio_stations()

        with self.assertRaisesRegex(ToolError, "two-letter"):
            main.search_radio_stations(country_code="USA")

        with self.assertRaisesRegex(ToolError, "must not be empty"):
            main.search_radio_stations(name="  ")

    def test_limits_results_to_at_most_fifty(self) -> None:
        with self.assertRaisesRegex(ToolError, "between 1 and 50"):
            main.search_radio_stations(name="Jazz", limit=51)

        with self.assertRaisesRegex(ToolError, "between 1 and 50"):
            main.search_radio_stations(name="Jazz", limit=True)

        self.assertIsNone(self.browser.search_arguments)


if __name__ == "__main__":
    unittest.main()
