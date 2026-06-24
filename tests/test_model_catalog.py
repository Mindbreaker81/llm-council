import unittest

from backend.model_catalog import (
    filter_models,
    is_free_model,
    normalize_model,
    validate_custom_council_from_catalog,
)


def model(
    model_id,
    *,
    prompt="0",
    completion="0",
    input_modalities=None,
    output_modalities=None,
    context_length=128000,
):
    return {
        "id": model_id,
        "name": model_id,
        "pricing": {
            "prompt": prompt,
            "completion": completion,
        },
        "architecture": {
            "input_modalities": input_modalities or ["text"],
            "output_modalities": output_modalities or ["text"],
        },
        "top_provider": {
            "context_length": context_length,
        },
        "supported_parameters": ["tools", "reasoning"],
    }


class ModelCatalogTests(unittest.TestCase):
    def test_detects_free_models_from_decimal_pricing(self):
        self.assertTrue(is_free_model(model("free/model", prompt="0.000000", completion="0")))
        self.assertFalse(is_free_model(model("paid/model", prompt="0.0000001", completion="0")))

    def test_normalizes_price_per_million(self):
        normalized = normalize_model(model("paid/model", prompt="0.000001", completion="0.000002"))
        self.assertEqual(normalized["price_per_million"]["prompt"], "1.000000")
        self.assertEqual(normalized["price_per_million"]["completion"], "2.000000")

    def test_filters_text_models(self):
        catalog = [
            model("text/model"),
            model("image-only/model", input_modalities=["image"], output_modalities=["image"]),
        ]
        filtered = filter_models(catalog, text_only=True)
        self.assertEqual([item["id"] for item in filtered], ["text/model"])

    def test_validates_custom_council(self):
        catalog = [model("a/model"), model("b/model"), model("openrouter/free")]
        result = validate_custom_council_from_catalog(catalog, ["a/model", "b/model"], "a/model")
        self.assertTrue(result["valid"])
        self.assertEqual(result["model_ids"], ["a/model", "b/model"])
        self.assertEqual(result["chairman_model_id"], "a/model")

    def test_rejects_incompatible_custom_model(self):
        catalog = [
            model("text/model"),
            model("audio/model", input_modalities=["audio"], output_modalities=["audio"]),
        ]
        result = validate_custom_council_from_catalog(catalog, ["text/model", "audio/model"], "text/model")
        self.assertFalse(result["valid"])
        self.assertIn("Model does not support text input and output: audio/model", result["errors"])


if __name__ == "__main__":
    unittest.main()
