# AI benchmark runtime artifacts

This directory is a visible repository scaffold only. Benchmark outputs are generated at runtime and must not be committed.

- GitHub live runs write to `${{ runner.temp }}/ai-bench-yandex-live` and upload a sanitized artifact.
- Local runs must pass an explicit `--output-dir`; prefer a temporary directory outside the repository.
- Do not place API keys, credentials, production resumes, user profiles, or other production PII here.
