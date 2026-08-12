PROF-001 STRUCTURED CAREER PROFILE CANDIDATE v1.4.20

Baseline: ai-career-agent-site-main (14).zip from current GitHub main/Render.
Candidate revision: 20260811_0010.
Suggested branch: prof-001-candidate-v1.4.20.

Primary behavior:
  - owner-only current profile and immutable version history;
  - contacts, goals, geography, salary, skills, employment,
    achievements, education and languages;
  - incomplete profile support and deterministic completion indicator;
  - explicit manual confirmation/save boundary;
  - no-op save does not create a version;
  - stale editor returns a safe conflict instead of overwriting data;
  - profile responses are no-store; POST is protected by login, CSRF and rate limits.

Required after branch upload:
  1. Green Pull Request workflow including the dedicated PROF-001 gate.
  2. Merge only after every CI step is green.
  3. Render deploy and /health/ready current=expected=20260811_0010.
  4. Real owner create/update/history/no-op/stale-editor E2E.
  5. Second-user isolation and restart persistence smoke.
  6. AUTH-001/AUTH-002/dashboard/vacancy-search regression smoke and clean logs.

No secrets or personal profile fixtures are included. Do not publish profile facts, cookies or database credentials in screenshots/log excerpts.
