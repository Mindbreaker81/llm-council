"""Tests for the OpenRouter API client."""

import unittest
from unittest.mock import patch, AsyncMock

from backend.openrouter import extract_final_content, get_fallback_model, query_model
from backend.config import MODEL_FALLBACK_MAP


class ExtractFinalContentTests(unittest.TestCase):
    def test_removes_think_tags(self):
        text = "<think>reasoning</think>final answer"
        self.assertEqual(extract_final_content(text), "final answer")

    def test_removes_reasoning_tags(self):
        text = "<reasoning>reasoning</reasoning>final answer"
        self.assertEqual(extract_final_content(text), "final answer")

    def test_returns_original_when_empty(self):
        text = "<think>only</think>"
        result = extract_final_content(text)
        self.assertEqual(result, text)


class GetFallbackModelTests(unittest.TestCase):
    def test_known_free_model_maps_to_paid(self):
        for free_model, paid_model in MODEL_FALLBACK_MAP.items():
            self.assertEqual(get_fallback_model(free_model), paid_model)

    def test_non_free_model_returns_none(self):
        self.assertIsNone(get_fallback_model("openai/gpt-4o"))


class QueryModelTests(unittest.IsolatedAsyncioTestCase):
    async def test_successful_response(self):
        fake_response = {
            "choices": [{"message": {"content": "answer"}}]
        }
        with patch("backend.openrouter._post_openrouter", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = fake_response
            result = await query_model("openai/gpt-4o", [{"role": "user", "content": "hi"}])
            self.assertEqual(result["content"], "answer")
            self.assertEqual(result["original_content"], "answer")

    async def test_fallback_used_on_failure(self):
        free_model = "google/gemini-2.5-flash:free"
        fallback_model = MODEL_FALLBACK_MAP[free_model]
        fake_response = {
            "choices": [{"message": {"content": "fallback answer"}}]
        }

        with patch("backend.openrouter._post_openrouter", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = [Exception("model unavailable"), fake_response]
            result = await query_model(free_model, [{"role": "user", "content": "hi"}])
            self.assertEqual(result["content"], "fallback answer")
            self.assertEqual(mock_post.call_count, 2)
            self.assertEqual(mock_post.call_args_list[0].args[0], free_model)
            self.assertEqual(mock_post.call_args_list[1].args[0], fallback_model)

    async def test_returns_none_when_fallback_fails(self):
        free_model = "google/gemini-2.5-flash:free"
        with patch("backend.openrouter._post_openrouter", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = Exception("model unavailable")
            result = await query_model(free_model, [{"role": "user", "content": "hi"}])
            self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
