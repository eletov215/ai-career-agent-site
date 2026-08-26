from __future__ import annotations

import io
import json
import os
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from evals.ai_bench.errors import ConfigurationError, ProviderError
from evals.ai_bench.models import BenchmarkCase, ProviderSpec
from evals.ai_bench.providers import OpenAICompatibleProvider

ROOT = Path(__file__).resolve().parents[1]


class _FakeHTTPResponse:
    def __init__(self, payload: dict, *, status: int = 200) -> None:
        self.payload = payload
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, _limit: int) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class _RawHTTPResponse:
    def __init__(self, raw: bytes, *, status: int = 200) -> None:
        self.raw = raw
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, _limit: int) -> bytes:
        return self.raw


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
            required_unverified_evidence_ids=(),
            required_caveat_evidence_ids=(),
            match_requirements=(),
            manual_rubric=(),
            tags=(),
            source_path=ROOT / "evals/fixtures/cases/resume-analysis-ru-01.json",
        )

    def _spec(self, **overrides) -> ProviderSpec:
        options = {
            "endpoint": "https://ai.api.cloud.yandex.net/v1/chat/completions",
            "api_key_env": "AI_BENCH_TEST_KEY",
            "auth_scheme": "Api-Key",
            "extra_headers_env": {"OpenAI-Project": "AI_BENCH_TEST_FOLDER"},
            "model_env": "AI_BENCH_TEST_MODEL",
            "metadata_model": "aliceai-llm/latest",
            "response_schema_mode": "json_schema",
            "max_retries": 1,
            "retry_backoff_seconds": 0,
        }
        options.update(overrides)
        return ProviderSpec(
            provider_id="yandex-test",
            adapter="openai_compatible",
            enabled=True,
            options=options,
        )

    def _env(self) -> dict[str, str]:
        return {
            "AI_BENCH_TEST_KEY": "test-secret-value",
            "AI_BENCH_TEST_FOLDER": "folder-123",
            "AI_BENCH_TEST_MODEL": "gpt://folder-123/aliceai-llm/latest",
        }

    def test_yandex_request_uses_api_key_project_model_env_and_json_schema(self) -> None:
        schema = {"type": "object", "properties": {"summary": {"type": "string"}}, "required": ["summary"]}
        envelope = {
            "choices": [{"finish_reason": "stop", "message": {"content": '{"summary":"ok"}'}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 4},
        }
        captured = {}

        def fake_urlopen(request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            return _FakeHTTPResponse(envelope)

        with patch.dict(os.environ, self._env(), clear=False), patch("urllib.request.urlopen", side_effect=fake_urlopen):
            provider = OpenAICompatibleProvider(self._spec(), ROOT, 45)
            response = provider.invoke(self._case(), schema)

        request = captured["request"]
        self.assertEqual(request.get_header("Authorization"), "Api-Key test-secret-value")
        self.assertEqual(request.get_header("Openai-project"), "folder-123")
        body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(body["model"], "gpt://folder-123/aliceai-llm/latest")
        self.assertEqual(body["response_format"]["type"], "json_schema")
        self.assertEqual(body["response_format"]["json_schema"]["schema"], schema)
        self.assertNotIn("strict", body["response_format"]["json_schema"])
        self.assertEqual(response.content, {"summary": "ok"})
        self.assertEqual(response.input_tokens, 12)
        self.assertEqual(response.output_tokens, 4)
        self.assertEqual(response.metadata["model"], "aliceai-llm/latest")
        self.assertEqual(response.metadata["mode"], "live")
        diagnostics = response.metadata["provider_diagnostics"]
        self.assertEqual(diagnostics["http_status"], 200)
        self.assertEqual(diagnostics["finish_reason"], "stop")
        self.assertEqual(diagnostics["content_type"], "str")
        self.assertEqual(diagnostics["retry_count"], 0)

    def test_json_schema_strict_is_sent_only_when_explicitly_configured(self) -> None:
        schema = {"type": "object", "properties": {"summary": {"type": "string"}}}
        envelope = {"choices": [{"message": {"content": '{"summary":"ok"}'}}]}
        captured = {}

        def fake_urlopen(request, timeout):
            captured["request"] = request
            return _FakeHTTPResponse(envelope)

        with patch.dict(os.environ, self._env(), clear=False), patch("urllib.request.urlopen", side_effect=fake_urlopen):
            OpenAICompatibleProvider(self._spec(response_schema_strict=True), ROOT, 45).invoke(self._case(), schema)

        body = json.loads(captured["request"].data.decode("utf-8"))
        self.assertTrue(body["response_format"]["json_schema"]["strict"])

    def test_invalid_json_schema_strict_type_is_rejected(self) -> None:
        with patch.dict(os.environ, self._env(), clear=False):
            with self.assertRaises(ConfigurationError):
                OpenAICompatibleProvider(self._spec(response_schema_strict="false"), ROOT, 45)

    def test_missing_model_environment_variable_fails_closed(self) -> None:
        env = {
            "AI_BENCH_TEST_KEY": "test-secret-value",
            "AI_BENCH_TEST_FOLDER": "folder-123",
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ConfigurationError):
                OpenAICompatibleProvider(self._spec(), ROOT, 45)

    def test_invalid_auth_scheme_is_rejected(self) -> None:
        with patch.dict(os.environ, self._env(), clear=False):
            with self.assertRaises(ConfigurationError):
                OpenAICompatibleProvider(self._spec(auth_scheme="Basic"), ROOT, 45)

    def test_more_than_one_retry_is_rejected(self) -> None:
        with patch.dict(os.environ, self._env(), clear=False):
            with self.assertRaises(ConfigurationError):
                OpenAICompatibleProvider(self._spec(max_retries=2), ROOT, 45)

    def test_http_500_is_retried_once_and_retry_is_recorded(self) -> None:
        schema = {"type": "object"}
        http_error = urllib.error.HTTPError(
            url="https://ai.api.cloud.yandex.net/v1/chat/completions",
            code=500,
            msg="server error",
            hdrs=None,
            fp=io.BytesIO(b'{"internal":"not persisted"}'),
        )
        success = _FakeHTTPResponse({"choices": [{"message": {"content": '{"summary":"ok"}'}}]})
        with patch.dict(os.environ, self._env(), clear=False), patch(
            "urllib.request.urlopen", side_effect=[http_error, success]
        ) as mocked:
            response = OpenAICompatibleProvider(self._spec(), ROOT, 45).invoke(self._case(), schema)
        self.assertEqual(mocked.call_count, 2)
        diagnostics = response.metadata["provider_diagnostics"]
        self.assertEqual(diagnostics["retry_count"], 1)
        self.assertEqual(diagnostics["retry_reasons"], ["http_500"])
        self.assertNotIn("not persisted", json.dumps(response.metadata))

    def test_http_400_is_not_retried(self) -> None:
        http_error = urllib.error.HTTPError(
            url="https://ai.api.cloud.yandex.net/v1/chat/completions",
            code=400,
            msg="bad request",
            hdrs=None,
            fp=io.BytesIO(b"sensitive body must not be recorded"),
        )
        with patch.dict(os.environ, self._env(), clear=False), patch(
            "urllib.request.urlopen", side_effect=http_error
        ) as mocked:
            with self.assertRaises(ProviderError) as ctx:
                OpenAICompatibleProvider(self._spec(), ROOT, 45).invoke(self._case(), {"type": "object"})
        self.assertEqual(mocked.call_count, 1)
        self.assertEqual(ctx.exception.diagnostics["http_status"], 400)
        self.assertEqual(ctx.exception.diagnostics["retry_count"], 0)
        self.assertNotIn("sensitive body", str(ctx.exception))
        self.assertNotIn("sensitive body", json.dumps(ctx.exception.diagnostics))

    def test_null_content_is_retried_once(self) -> None:
        null_envelope = {
            "choices": [{"finish_reason": "stop", "message": {"content": None}}],
        }
        success = _FakeHTTPResponse({"choices": [{"message": {"content": '{"summary":"ok"}'}}]})
        with patch.dict(os.environ, self._env(), clear=False), patch(
            "urllib.request.urlopen", side_effect=[_FakeHTTPResponse(null_envelope), success]
        ) as mocked:
            response = OpenAICompatibleProvider(self._spec(), ROOT, 45).invoke(self._case(), {"type": "object"})
        self.assertEqual(mocked.call_count, 2)
        diagnostics = response.metadata["provider_diagnostics"]
        self.assertEqual(diagnostics["retry_reasons"], ["content_null"])
        self.assertEqual(diagnostics["retry_count"], 1)

    def test_invalid_json_envelope_is_retried_once(self) -> None:
        success = _FakeHTTPResponse({"choices": [{"message": {"content": '{"summary":"ok"}'}}]})
        with patch.dict(os.environ, self._env(), clear=False), patch(
            "urllib.request.urlopen", side_effect=[_RawHTTPResponse(b"not-json"), success]
        ) as mocked:
            response = OpenAICompatibleProvider(self._spec(), ROOT, 45).invoke(self._case(), {"type": "object"})
        self.assertEqual(mocked.call_count, 2)
        self.assertEqual(response.metadata["provider_diagnostics"]["retry_reasons"], ["envelope_invalid_json"])

    def test_refusal_is_diagnosed_without_retry_or_refusal_text(self) -> None:
        envelope = {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"content": None, "refusal": "private refusal text that must not persist"},
                }
            ]
        }
        with patch.dict(os.environ, self._env(), clear=False), patch(
            "urllib.request.urlopen", return_value=_FakeHTTPResponse(envelope)
        ) as mocked:
            with self.assertRaises(ProviderError) as ctx:
                OpenAICompatibleProvider(self._spec(), ROOT, 45).invoke(self._case(), {"type": "object"})
        self.assertEqual(mocked.call_count, 1)
        diagnostics = ctx.exception.diagnostics
        self.assertTrue(diagnostics["refusal_present"])
        self.assertEqual(diagnostics["reason"], "model_refusal")
        self.assertEqual(diagnostics["retry_count"], 0)
        persisted = json.dumps(diagnostics) + str(ctx.exception)
        self.assertNotIn("private refusal text", persisted)

    def test_malformed_content_after_retry_exposes_only_shape_diagnostics(self) -> None:
        malformed = _FakeHTTPResponse(
            {"choices": [{"finish_reason": "length", "message": {"content": "not-json"}}]}
        )
        with patch.dict(os.environ, self._env(), clear=False), patch(
            "urllib.request.urlopen", side_effect=[malformed, malformed]
        ):
            with self.assertRaises(ProviderError) as ctx:
                OpenAICompatibleProvider(self._spec(), ROOT, 45).invoke(self._case(), {"type": "object"})
        diagnostics = ctx.exception.diagnostics
        self.assertEqual(diagnostics["reason"], "content_invalid_json")
        self.assertEqual(diagnostics["finish_reason"], "length")
        self.assertEqual(diagnostics["content_type"], "str")
        self.assertEqual(diagnostics["attempt_count"], 2)
        self.assertEqual(diagnostics["retry_count"], 1)
        self.assertNotIn("not-json", json.dumps(diagnostics))


if __name__ == "__main__":
    unittest.main()
