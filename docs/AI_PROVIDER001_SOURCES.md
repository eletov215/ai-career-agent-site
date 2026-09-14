# AI Career Agent - AI-PROVIDER-001 / External source register

| Поле | Значение |
|---|---|
| Document | AI_PROVIDER001_SOURCES |
| Package | AI-PROVIDER-001 |
| Version | 1.0 |
| Date | 2026-09-14 |
| Status | External sources unchanged; owner strategy approved; final ordinary CI pending |
| Scope | Architecture and offline validation only; no production AI activation |
| Schema revision | 20260819_0014 (unchanged) |

## 1. Method and evidence classes

Checked on 2026-09-14 against official primary sources only. Provider-source facts are listed below. Application caps, routing and release rules in this package are new design choices for owner approval, not provider promises.

The GitHub ZIP and final benchmark/human-review files are project evidence. No private billing console, production API key, future VPS, customer contract amendment or user-data flow was inspected in this research. Platform documentation can change; recheck before activation and whenever terms, model or billing changes.

## 2. Official source register

### S1. AI Studio pricing

Synchronous Alice prices: RUB 0.5 input / 1.2 output per 1000 tokens, VAT included; USD 0.00409836 / 0.009836064 per 1000, VAT excluded. These are separate tariff columns, not an exchange-rate conversion.

Source: [AI Studio pricing](https://aistudio.yandex.ru/ru/docs/ai-studio/pricing). Checked: 2026-09-14.

### S2. AI Studio model lifecycle

Alice is available as a model family. Model identifiers and retirement policy must be checked before activation. Benchmark metadata identifies an alias, not a verified immutable model revision.

Source: [AI Studio model lifecycle](https://aistudio.yandex.ru/ru/docs/ai-studio/concepts/generation/models). Checked: 2026-09-14.

### S3. AI Studio quotas and limits

The documented default synchronous generation concurrency is 10. Actual account quotas can differ. Asynchronous text results are retained for three days; this design excludes that mode.

Source: [AI Studio quotas and limits](https://aistudio.yandex.ru/ru/docs/ai-studio/concepts/limits). Checked: 2026-09-14.

### S4. Disable request logging

Request logging is on by default. The documented per-request control is x-data-logging-enabled: false. This technical instruction must be read with the contractual timing in S5.

Source: [Disable request logging](https://aistudio.yandex.ru/ru/docs/ai-studio/operations/disable-logging). Checked: 2026-09-14.

### S5. AI Studio service terms

Version effective 2026-04-28. Sections 1.2.2 and 3.15 distinguish product integration from simple API resale. Sections 3.3, 3.11.4 and 3.14 address output review, restricted human-authorship claims and provider mentions. Sections 5.4.1-5.6 address data restrictions, opting out of training/debugging, a 24-hour disablement period and necessary transient processing.

Source: [AI Studio service terms](https://yandex.ru/legal/cloud_terms_yandex_ai_studio/ru/). Checked: 2026-09-14.

### S6. Cloud data processing agreement

Version effective 2025-12-05. Sections 2.1.1-2.1.2 require appropriate legal grounds and purpose-limited data. Section 2.2.5 specifies Russian database location except when the customer chooses infrastructure outside Russia. This is not a compliance certificate for our entire application.

Source: [Cloud data processing agreement](https://yandex.ru/legal/cloud_dpa/ru/). Checked: 2026-09-14.

### S7. Cloud platform terms

Version effective 2026-09-07. Customer obligations and platform conditions apply in addition to service-specific rules. Account eligibility and the actual deployment contract must be checked, not inferred from UI country selection.

Source: [Cloud platform terms](https://yandex.ru/legal/cloud_termsofuse/ru/). Checked: 2026-09-14.

### S8. Cloud payment methods

The payment FAQ describes RUB payment for Russian tax residents with supported Russian-issued cards or SBP. For Belarus tax residents it describes RUB payment with Belarus-issued Belkart or Russian-issued Mir. Actual owner billing configuration was not inspected.

Source: [Cloud payment methods](https://yandex.cloud/ru/docs/billing/qa/payment). Checked: 2026-09-14.

### S9. Service-account API keys

API keys can be scoped and time-limited. The proposed production key uses the language-model execution scope instead of unrestricted application credentials.

Source: [Service-account API keys](https://yandex.cloud/en/docs/iam/concepts/authorization/api-key). Checked: 2026-09-14.

### S10. AI Studio access management

The language-model user role exists for model use. Least privilege is required; broad editor permissions are not part of the proposed production configuration.

Source: [AI Studio access management](https://aistudio.yandex.ru/docs/en/ai-studio/security/index.html). Checked: 2026-09-14.

## 3. Unresolved matters, not assumed facts

Actual billing currency, account eligibility, deployed quota, immutable model revision, request opt-out effective time, operational-metadata retention and future production-IP transport are not proven by the benchmark. The policy records these as activation prerequisites instead of fabricating values.

The terms and DPA are input to LEGAL-001, not a legal opinion. Their applicability to the actual operator, chosen regions, special categories and public disclosures needs a qualified review. The April AI Studio and September platform terms have different effective dates; both must be considered. No blanket regional availability guarantee is made.

## 4. Implementation and rollback boundary

This source register makes no API or account changes. Reverting it cannot change provider terms or restore data. Keep the dated register with each decision version and recheck the live official pages before production activation.

## 5. Next action and version log

Review the ADR and ordinary CI, then carry the unresolved activation checklist into LEGAL-001 and AI-001.

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-09-14 | Official pricing, terms, data policy, geography/payment and access sources checked |
