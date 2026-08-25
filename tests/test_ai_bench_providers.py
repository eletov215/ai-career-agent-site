from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from evals.ai_bench.errors import ConfigurationError
from evals.ai_bench.models import BenchmarkCase, ProviderSpec
from evals.ai_bench.providers import OpenAICompatibleProvider

ROOT = Path(__file__).resolve().parents[1]


class _FakeHTTPResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, _limit: int) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class OpenAICompatibleProviderTests(unittest.TestCase):
    def _case(self) -> BenchmarkCase:
        return BenchmarkCase(
            case_id="case-1",
            task="resume_analysis",
            language="ru",
            synthetic=True,
            schema_path=ROOT / "evals/schemas/resume_analysis.schema.json",
            messages=(
                {"role": "system", "content": "Return JSON."},
                {"role": "user", "content": "Synthetic input."},
            ),
            source_facts=(),
            required_paths=(),
            required_evidence_ids=(),
            grounding_requirements=(),
            forbidden_claims=(),
            generated_numeric_paths=(),
            manual_rubric=(),
            tags=(),
            source_path=ROOT / "evals/fixtures/cases/resume-analysis-ru-01.json",
        )

    def _spec(self) -> ProviderSpec:
        return ProviderSpec(
            provider_id="yandex-test",
            adapter="openai_compatible",
            enabled=True,
            options={
                "endpoint": "https://ai.api.cloud.yandex.net/v1/chat/completions",
                "api_key_env": "AI_BENCH_TEST_KEY",
                "auth_scheme": "Api-Key",
                "extra_headers_env": {"OpenAI-Project": "AI_BENCH_TEST_FOLDER"},
                "model_env": "AI_BENCH_TEST_MODEL",
                "metadata_model": "aliceai-llm/latest",
                "response_schema_mode": "json_schema",
            },
        )

    def test_yandex_request_uses_api_key_project_model_env_and_json_schema(self) -> None:
        schema = {"type": "object", "properties": {"summary": {"type": "string"}}, "required": ["summary"]}
        envelope = {
            "choices": [{"message": {"content": '{"summary":"ok"}'}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 4},
        }
        captured = {}

        def fake_urlopen(request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            return _FakeHTTPResponse(envelope)

        env = {
            "AI_BENCH_TEST_KEY": "test-secret-value",
            "AI_BENCH_TEST_FOLDER": "folder-123",
            "AI_BENCH_TEST_MODEL": "gpt://folder-123/aliceai-llm/latest",
        }
        with patch.dict(os.environ, env, clear=False), patch("urllib.request.urlopen", side_effect=fake_urlopen):
            provider = OpenAICompatibleProvider(self._spec(), ROOT, 45)
            response = provider.invoke(self._case(), schema)

        request = captured["request"]
        self.assertEqual(request.get_header("Authorization"), "Api-Key test-secret-value")
        self.assertEqual(request.get_header("Openai-project"), "folder-123")
        body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(body["model"], "gpt://folder-123/aliceai-llm/latest")
        self.assertEqual(body["response_format"]["type"], "json_schema")
        self.assertEqual(body["response_format"]["json_schema"]["schema"], schema)
        self.assertFalse(body["response_format"]["json_schema"]["strict"])
        self.assertEqual(response.content, {"summary": "ok"})
        self.assertEqual(response.input_tokens, 12)
        self.assertEqual(response.output_tokens, 4)
        self.assertEqual(response.metadata["model"], "aliceai-llm/latest")
        self.assertEqual(response.metadata["mode"], "live")

    def test_missing_model_environment_variable_fails_closed(self) -> None:
        env = {
            "AI_BENCH_TEST_KEY": "test-secret-value",
            "AI_BENCH_TEST_FOLDER": "folder-123",
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ConfigurationError):
                OpenAICompatibleProvider(self._spec(), ROOT, 45)

    def test_invalid_auth_scheme_is_rejected(self) -> None:
        spec = self._spec()
        options = dict(spec.options)
        options["auth_scheme"] = "Basic"
        bad = ProviderSpec(provider_id=spec.provider_id, adapter=spec.adapter, enabled=True, options=options)
        env = {
            "AI_BENCH_TEST_KEY": "test-secret-value",
            "AI_BENCH_TEST_FOLDER": "folder-123",
            "AI_BENCH_TEST_MODEL": "gpt://folder-123/aliceai-llm/latest",
        }
        with patch.dict(os.environ, env, clear=False):
            with self.assertRaises(ConfigurationError):
                OpenAICompatibleProvider(bad, ROOT, 45)


if __name__ == "__main__":
    unittest.main()
