import unittest

from backend.config import COUNCIL_TYPE_CUSTOM, COUNCIL_TYPE_ECONOMIC
from backend.council import get_council_config, parse_ranking_from_text


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


if __name__ == "__main__":
    unittest.main()
