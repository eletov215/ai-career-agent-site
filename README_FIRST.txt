SEC-001 CI fix v1.2.9

Copy these files into the current sec-001-security-baseline branch with replacement:
- config.py
- security.py
- tests/test_config.py
- .github/workflows/ci.yml

Commit message:
fix: correct SEC-001 CSRF and host validation

Do not merge the pull request until the new GitHub Actions run is fully green.
CI trigger check 2026-08-06

