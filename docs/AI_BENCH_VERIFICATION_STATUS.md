# AI Career Agent - AI-BENCH-001 Verification Status

| Поле | Значение |
|---|---|
| Документ | AI_BENCH_VERIFICATION_STATUS |
| Версия | 1.2 |
| Дата | 25 августа 2026 |
| Пакет | AI-BENCH-001 live Yandex candidate |
| Статус | НУЖНА ПРОВЕРКА LIVE COMPARATIVE RUN + MANUAL RUBRIC |
| Production revision | `20260819_0014` |

## 1. GitHub hotfix gate

User-provided GitHub screenshots confirm run `#184` completed successfully:

- `Python tests` - GREEN;
- `AI-BENCH-001 package gate` - GREEN;
- the previous unsupported-number false positive is no longer reproduced.

The remaining annotation was a Node.js runtime deprecation warning in older action versions, not a test failure. The live candidate updates the AI-BENCH checkout/setup-python actions to v6.

## 2. Manual Yandex access gate

The user created an isolated Yandex Cloud folder `ai-career-agent-ai`, a service account `ai-career-agent-bench`, and assigned `ai.languageModels.user`. Alice AI LLM was opened in AI Studio Playground and passed a short career-match smoke without inventing experience.

An API key was then created for the benchmark service account. The user stored the secret value and folder ID only as GitHub Actions Secrets:

```text
AI_BENCH_YANDEX_API_KEY
AI_BENCH_YANDEX_FOLDER_ID
```

Secret values are not present in the repository or this document.

## 3. Live candidate implementation

`evals 1.1.0` adds:

- `evals/config/yandex-live.json`;
- manual-only `.github/workflows/ai-bench-live.yml`;
- Alice AI LLM, Alice AI LLM Flash and YandexGPT Pro 5.1 candidates;
- current OpenAI-compatible Yandex endpoint and model URI contract;
- `Api-Key` authorization and `OpenAI-Project` header from environment;
- per-case `json_schema` structured output;
- current synchronous USD pricing snapshot for cost estimation;
- sanitized run/report/response artifact upload;
- a transport gate that fails on provider/API errors but does not turn model quality failures into infrastructure failures;
- `evals/.gitignore` and `evals/artifacts/.gitkeep` to prevent runtime artifacts from being committed.

## 4. Local verification

| Проверка | Результат |
|---|---|
| Deterministic AI-BENCH package gate | PASS |
| AI-BENCH unittest discovery | 14 tests PASS |
| Yandex provider request/header/schema unit coverage | PASS |
| Live config validation with dummy environment | PASS, 3 providers |
| Repository hygiene after cleanup | PASS |
| Document structure | PASS |
| Production route/migration isolation | PASS |

No live API request was executed locally because the API key remains only in GitHub Secrets.

## 5. Required external run

After this candidate is uploaded to GitHub:

1. confirm ordinary CI remains green;
2. open Actions -> `AI-BENCH-001 Live Yandex` -> `Run workflow`;
3. wait for `Yandex live comparative benchmark`;
4. download the `ai-bench-001-yandex-live-<run_id>` artifact;
5. review `run.json`, `report.md` and sanitized responses;
6. complete the human writing-quality rubric;
7. only then make the AI-PROVIDER-001 provider decision.

## 6. Status decision

**AI-BENCH-001 remains open.** Benchmark infrastructure and credentials are ready, but live comparative evidence and manual review do not yet exist.

`AI-PROVIDER-001` remains **ЗАБЛОКИРОВАН**.

## 7. Version log

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 24.08.2026 | Initial benchmark implementation candidate and external-run gate defined. |
| 1.1 | 24.08.2026 | Recorded CI rejection; fixed root-container numeric false positive; hotfix awaiting rerun. |
| 1.2 | 25.08.2026 | Hotfix GitHub run confirmed green; Alice Playground/service account/GitHub Secrets confirmed; live Yandex workflow candidate prepared. |
