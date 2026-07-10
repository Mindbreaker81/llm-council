"""Tests for model catalog security guardrails."""

import unittest

from backend.model_catalog import validate_custom_council_from_catalog


class CostGuardrailTests(unittest.TestCase):
    def test_expensive_custom_council_is_rejected(self):
        catalog = [
            {
                "id": "expensive/model-a",
                "name": "Expensive Model A",
                "context_length": 128000,
                "pricing": {"prompt": "0.1", "completion": "0.2"},
                "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]},
            },
            {
                "id": "expensive/model-b",
                "name": "Expensive Model B",
                "context_length": 128000,
                "pricing": {"prompt": "0.1", "completion": "0.2"},
                "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]},
            },
            {
                "id": "expensive/chairman",
                "name": "Expensive Chairman",
                "context_length": 128000,
                "pricing": {"prompt": "0.1", "completion": "0.2"},
                "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]},
            },
        ]

        result = validate_custom_council_from_catalog(
            catalog,
            ["expensive/model-a", "expensive/model-b"],
            "expensive/chairman",
        )
        self.assertFalse(result["valid"])
        self.assertTrue(
            any("exceeds" in error.lower() for error in result["errors"]),
            f"Expected cost error, got {result['errors']}",
        )

    def test_cheap_custom_council_is_allowed(self):
        catalog = [
            {
                "id": "cheap/model-a",
                "name": "Cheap Model A",
                "context_length": 128000,
                "pricing": {"prompt": "0.0000001", "completion": "0.0000001"},
                "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]},
            },
            {
                "id": "cheap/model-b",
                "name": "Cheap Model B",
                "context_length": 128000,
                "pricing": {"prompt": "0.0000001", "completion": "0.0000001"},
                "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]},
            },
        ]

        result = validate_custom_council_from_catalog(
            catalog,
            ["cheap/model-a", "cheap/model-b"],
            "cheap/model-a",
        )
        self.assertTrue(result["valid"])


if __name__ == "__main__":
    unittest.main()
