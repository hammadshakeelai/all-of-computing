import json
import os
import unittest
from unittest.mock import patch

from learning.providers import OpenAIProvider, ProviderError


class Response:
    def __init__(self, data):
        self.data = json.dumps(data).encode()

    def read(self):
        return self.data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class ProviderTests(unittest.TestCase):
    def test_responses_payload_and_output_contract(self):
        payload = {"status": "completed", "output": [{"content": [{"type": "output_text", "text": json.dumps({"reply": "Grounded explanation", "source_ids": ["source-1"]})}]}], "usage": {"input_tokens": 30}}
        with patch.dict(os.environ, {"OPENAI_API_KEY": "synthetic-key"}), patch("urllib.request.urlopen", return_value=Response(payload)) as transport:
            result, usage = OpenAIProvider("test-model").run("teach", {"source_ids": ["source-1"]})
            request = transport.call_args.args[0]
            body = json.loads(request.data)
            self.assertEqual(request.full_url, "https://api.openai.com/v1/responses")
            self.assertFalse(body["store"])
            self.assertEqual(body["text"]["format"]["type"], "json_schema")
            self.assertTrue(body["text"]["format"]["strict"])
            self.assertEqual(result["source_ids"], ["source-1"])
            self.assertEqual(usage["input_tokens"], 30)

    def test_incomplete_response_is_not_accepted(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "synthetic-key"}), patch("urllib.request.urlopen", return_value=Response({"status": "incomplete", "output": []})):
            with self.assertRaises(ProviderError):
                OpenAIProvider("test-model").run("teach", {})

    def test_refusal_is_not_treated_as_feedback(self):
        payload = {"status": "completed", "output": [{"content": [{"type": "refusal", "refusal": "Cannot answer"}]}]}
        with patch.dict(os.environ, {"OPENAI_API_KEY": "synthetic-key"}), patch("urllib.request.urlopen", return_value=Response(payload)):
            with self.assertRaises(ProviderError):
                OpenAIProvider("test-model").run("teach", {})

    def test_wrong_structured_field_type_is_rejected(self):
        payload = {"status": "completed", "output": [{"content": [{"type": "output_text", "text": '{"reply": 3, "source_ids": []}'}]}]}
        with patch.dict(os.environ, {"OPENAI_API_KEY": "synthetic-key"}), patch("urllib.request.urlopen", return_value=Response(payload)):
            with self.assertRaises(ProviderError):
                OpenAIProvider("test-model").run("teach", {})

    def test_no_key_no_network_call(self):
        with patch.dict(os.environ, {}, clear=True), patch("urllib.request.urlopen") as transport:
            with self.assertRaises(ProviderError):
                OpenAIProvider("test-model").run("teach", {})
            transport.assert_not_called()


if __name__ == "__main__":
    unittest.main()
