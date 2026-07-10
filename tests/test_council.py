import unittest
from unittest.mock import patch, AsyncMock

from backend.config import COUNCIL_TYPE_CUSTOM, COUNCIL_TYPE_ECONOMIC
from backend.council import (
    get_council_config,
    parse_ranking_from_text,
    calculate_aggregate_rankings,
    summarize_stage2_results,
)


class CouncilTests(unittest.TestCase):
    def test_get_council_config_returns_custom_selection(self):
        models, chairman = get_council_config(
            COUNCIL_TYPE_CUSTOM,
            {"models": ["a/model", "b/model"], "chairman_model": "a/model"},
        )
        self.assertEqual(models, ["a/model", "b/model"])
        self.assertEqual(chairman, "a/model")

    def test_get_council_config_requires_custom_payload(self):
        with self.assertRaises(ValueError):
            get_council_config(COUNCIL_TYPE_CUSTOM)

    def test_get_council_config_rejects_invalid_type(self):
        with self.assertRaises(ValueError):
            get_council_config("invalid")

    def test_existing_presets_still_resolve(self):
        models, chairman = get_council_config(COUNCIL_TYPE_ECONOMIC)
        self.assertGreaterEqual(len(models), 1)
        self.assertIsInstance(chairman, str)

    def test_parse_ranking_from_text(self):
        text = """Evaluation text.

FINAL RANKING:
1. Response B
2. Response A
"""
        self.assertEqual(parse_ranking_from_text(text), ["Response B", "Response A"])

    def test_parse_ranking_from_text_handles_word_boundaries(self):
        text = """FINAL RANKING:
1. Response AB
2. Response A
"""
        self.assertEqual(parse_ranking_from_text(text), ["Response AB", "Response A"])

    def test_parse_ranking_from_text_fallback_to_whole_text(self):
        text = "I think Response C is best, then Response A, then Response B."
        self.assertEqual(parse_ranking_from_text(text), ["Response C", "Response A", "Response B"])

    def test_parse_ranking_from_text_empty(self):
        self.assertEqual(parse_ranking_from_text(""), [])
        self.assertEqual(parse_ranking_from_text("No ranking here"), [])

    def test_calculate_aggregate_rankings_includes_unranked(self):
        stage2_results = [
            {"model": "m1", "ranking": "FINAL RANKING:\n1. Response B\n2. Response A"},
        ]
        label_to_model = {"Response A": "m1", "Response B": "m2", "Response C": "m3"}
        aggregate = calculate_aggregate_rankings(stage2_results, label_to_model)
        self.assertEqual(len(aggregate), 3)
        self.assertEqual(aggregate[0]["model"], "m2")
        self.assertEqual(aggregate[0]["average_rank"], 1.0)
        self.assertEqual(aggregate[1]["model"], "m1")
        self.assertEqual(aggregate[1]["average_rank"], 2.0)
        self.assertEqual(aggregate[2]["model"], "m3")
        self.assertIsNone(aggregate[2]["average_rank"])


class SummarizeTests(unittest.IsolatedAsyncioTestCase):
    async def test_summarize_stage2_results_uses_council_model(self):
        stage2_results = [
            {"model": "custom-model", "ranking": "1. Response A"},
        ]
        with patch("backend.council.query_model", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = {"content": "Concise summary"}
            result = await summarize_stage2_results(stage2_results, {})
            self.assertEqual(result, "Concise summary")
            mock_query.assert_awaited_once()
            self.assertEqual(mock_query.call_args.args[0], "custom-model")

    async def test_summarize_stage2_results_returns_fallback_when_empty(self):
        result = await summarize_stage2_results([], {})
        self.assertEqual(result, "No peer rankings available to summarize.")


if __name__ == "__main__":
    unittest.main()
