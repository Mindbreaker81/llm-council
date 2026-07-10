"""Integration tests for the FastAPI backend."""

import os
import tempfile
import unittest
from unittest.mock import patch, AsyncMock

from fastapi.testclient import TestClient

from backend import main
from backend.config import COUNCIL_TYPE_ECONOMIC, COUNCIL_TYPE_PREMIUM


class MainIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.data_dir = tempfile.mkdtemp()
        # Keep storage isolated during tests.
        main.storage.DATA_DIR = self.data_dir

    def tearDown(self):
        # Remove any conversation JSON files created by the tests.
        for filename in os.listdir(self.data_dir):
            path = os.path.join(self.data_dir, filename)
            if os.path.isfile(path):
                os.remove(path)
        os.rmdir(self.data_dir)

    def test_health_endpoint(self):
        with TestClient(main.app) as client:
            response = client.get("/health")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "ok")
            self.assertEqual(data["version"], "2.5.0")

    def test_create_conversation(self):
        with TestClient(main.app) as client:
            response = client.post("/api/conversations", json={})
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("id", data)
            self.assertEqual(data["council_type"], COUNCIL_TYPE_PREMIUM)

    def test_create_conversation_with_council_type(self):
        with TestClient(main.app) as client:
            response = client.post("/api/conversations", json={"council_type": COUNCIL_TYPE_ECONOMIC})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["council_type"], COUNCIL_TYPE_ECONOMIC)

    def test_create_conversation_invalid_type_returns_400(self):
        with TestClient(main.app) as client:
            response = client.post("/api/conversations", json={"council_type": "invalid"})
            self.assertEqual(response.status_code, 400)

    def test_send_message(self):
        with patch("backend.main.run_full_council", new_callable=AsyncMock) as mock_run, \
             patch("backend.main.generate_conversation_title", new_callable=AsyncMock) as mock_title:
            mock_run.return_value = (
                [{"model": "m1", "response": "answer 1", "original_response": "answer 1"}],
                [{"model": "m1", "ranking": "1. Response A", "parsed_ranking": ["Response A"]}],
                {"model": "chair", "response": "final"},
                {"label_to_model": {"Response A": "m1"}, "aggregate_rankings": [], "council_type": COUNCIL_TYPE_PREMIUM},
            )
            mock_title.return_value = "Test Title"

            with TestClient(main.app) as client:
                create_resp = client.post("/api/conversations", json={})
                conversation_id = create_resp.json()["id"]

                response = client.post(
                    f"/api/conversations/{conversation_id}/message",
                    json={"content": "hello", "council_type": COUNCIL_TYPE_PREMIUM},
                )
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertEqual(len(data["stage1"]), 1)
                self.assertEqual(data["stage3"]["response"], "final")
                self.assertEqual(data["metadata"]["council_type"], COUNCIL_TYPE_PREMIUM)

    def test_send_message_invalid_council_type_returns_400(self):
        with TestClient(main.app) as client:
            create_resp = client.post("/api/conversations", json={})
            conversation_id = create_resp.json()["id"]

            response = client.post(
                f"/api/conversations/{conversation_id}/message",
                json={"content": "hello", "council_type": "invalid"},
            )
            self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
