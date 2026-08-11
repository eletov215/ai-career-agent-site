AUTH-002 FIRST-PARTY OAUTH OWNERSHIP CANDIDATE v1.4.18

Baseline: ai-career-agent-site-main (12).zip from current GitHub main/Render.
Candidate revision: 20260811_0009.

Primary behavior:
  - first-party login required for provider connect;
  - OAuth state bound to User and AuthSession;
  - one external identity owner;
  - one provider slot per User;
  - encrypted owner-scoped reconnect/refresh/disconnect;
  - no email auto-link;
  - legacy provider browser keys cannot authorize.

Required after upload:
  1. Green full GitHub Actions including AUTH-002 dedicated gate.
  2. Render deploy and /health/ready current=expected=20260811_0009.
  3. Real HH bind/reconnect/disconnect.
  4. Real SuperJob bind/reconnect/disconnect.
  5. Cross-user ownership conflict negative smoke.

No secrets are included. External provider codes/tokens/client secrets stay only in environment/browser flow.
