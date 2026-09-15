# AI Career Agent - Source audit / AI-002 rebuild

| Поле | Значение |
|---|---|
| Version | 1.5.2 / 2026-09-15 |
| Baseline | ai-career-agent-site-main (32).zip |
| Archive comment | bc177dd6b970750f556f48f34dbd022a30e80a34 |
| SHA-256 | 161d52efebf1762a5dd73f0be890b7afb204d2a26e34f9237341eaf832075de9 |
| Files | 467 in original ZIP |
| Current package | AI-002 - NEEDS_VERIFICATION |

## 1. Precedence and source state

The owner-supplied ZIP is this rebuild's baseline. It represents accepted AI-001 with the dependency-free checker hotfix. No remote GitHub state beyond this archive is asserted. Separate canonical v1.5.1 documents establish AI-001 completion from CI #266 and staging 0015. Repository docs lagged behind them; their closure text is synchronized without inventing new deployment evidence.

## 2. Missing delivery boundary

Previously announced AI-002 candidate files were unavailable. They are not the source of this patch and their claimed checks are not reused. The present code was rebuilt against the preserved main (32) bytes and actually tested as documented in rebuild_verification.json. This is candidate r2, not an assertion of a recovered r1.

## 3. Reviewed change boundary

New report/review tables require 0016. Public runtime flags, accepted benchmark prompts/schemas/evals and AI-PROVIDER decisions remain unchanged. Each reviewed runtime difference has its old/new SHA-256 in docs/evidence/ai-002/change_boundary.json. Previous boundary manifests remain intact; successor checks explicitly chain them. PATCH composition is compared byte-for-byte against main (32); no deletes or runtime secrets are included.

## 4. Open gates

New GitHub CI, Neon migration and UI smoke remain required. Owner identity/jurisdiction and LEGAL-001 are unresolved. No real user resume was sent to a provider, no paid API was called and no remote deployment/database was modified during this rebuild.
