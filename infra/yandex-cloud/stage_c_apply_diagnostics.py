"""Fail-closed diagnostic for HOST-001 Stage C Terraform apply errors.

Print only fixed error classes, HTTP status codes and allowlisted Terraform
resource addresses. Never echo provider error text, which can contain credentials,
request metadata, generated keys or other private values.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

MAX_LOG_BYTES = 4_000_000

# Only resource addresses from the reviewed Stage C create-only plan.
REVIEWED_RESOURCES = frozenset(
    {
        "yandex_compute_instance.app",
        "yandex_iam_service_account.app",
        "yandex_iam_service_account_static_access_key.field_test_storage[0]",
        "yandex_lockbox_secret.field_test_storage[0]",
        "yandex_lockbox_secret.runtime",
        "yandex_lockbox_secret_iam_member.field_test_storage_payload[0]",
        "yandex_lockbox_secret_iam_member.runtime_payload",
        "yandex_mdb_postgresql_cluster.field_test_restore[0]",
        "yandex_mdb_postgresql_cluster.main",
        "yandex_mdb_postgresql_database.app",
        "yandex_mdb_postgresql_database.field_test_restore[0]",
        "yandex_mdb_postgresql_user.app",
        "yandex_mdb_postgresql_user.field_test_restore[0]",
        "yandex_resourcemanager_folder_iam_member.field_test_storage_uploader[0]",
        "yandex_storage_bucket.field_test[0]",
        "yandex_vpc_address.app",
        "yandex_vpc_network.main",
        "yandex_vpc_security_group.app",
        "yandex_vpc_security_group.database",
        "yandex_vpc_subnet.app",
        "yandex_vpc_subnet.db_secondary",
    }
)

# Output only these labels, never the matched text.
ERROR_CLASSES = (
    ("IAM_PERMISSION", r"permission.denied|permissiondenied|access.denied|accessdenied|forbidden|not.authorized"),
    ("AUTHENTICATION", r"unauthorized|unauthenticated|authentication.failed|invalid.credentials"),
    ("QUOTA_OR_CAPACITY", r"resourceexhausted|quota|capacity|insufficient.resources|limit.exceeded"),
    ("INVALID_ARGUMENT", r"invalidargument|invalid.argument|invalid.parameter|invalid.value|validation.error"),
    ("PREREQUISITE", r"failedprecondition|precondition.failed|preconditionfailed"),
    ("ALREADY_EXISTS", r"alreadyexists|already.exists|conflict"),
    ("NOT_FOUND", r"notfound|not.found|does.not.exist"),
    ("TRANSIENT_SERVICE", r"service.unavailable|unavailable|internal.error|too.many.requests"),
    ("TIMEOUT", r"deadlineexceeded|deadline.exceeded|time.?out|timed.out"),
    ("STATE_LOCK", r"error.acquiring.the.state.lock|failed.to.acquire.lock"),
)
RESOURCE_REF = re.compile(r"\bwith\s+(yandex_[a-z0-9_]+\.[a-z0-9_]+(?:\[[0-9]+\])?)", re.I)
STATUS_REF = re.compile(r"\b(?:StatusCode|HTTP.status|status.code)\s*[:= ]\s*([45][0-9]{2})\b", re.I)


def summarize(log_text: str) -> str:
    """Return a bounded report containing no untrusted substrings."""
    classes = [
        name
        for name, pattern in ERROR_CLASSES
        if re.search(pattern, log_text, flags=re.IGNORECASE)
    ]
    addresses = sorted(
        {
            value
            for value in RESOURCE_REF.findall(log_text)
            if value in REVIEWED_RESOURCES
        }
    )
    status_codes = sorted(set(STATUS_REF.findall(log_text)))
    return "\n".join(
        (
            "Terraform apply failed. Raw provider output withheld to protect secrets.",
            "Error class signals: " + (", ".join(classes[:6]) if classes else "UNCLASSIFIED"),
            "Reviewed resource addresses: "
            + (", ".join(addresses[:8]) if addresses else "NONE_DETECTED"),
            "HTTP statuses: " + (", ".join(status_codes[:6]) if status_codes else "NONE_DETECTED"),
            "Use Yandex Cloud audit/operation records for details; do not post raw provider logs.",
        )
    )


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("Terraform apply diagnostic expects one local log path.", file=sys.stderr)
        return 2
    try:
        with Path(args[0]).open("rb") as source:
            source.seek(0, 2)
            total = source.tell()
            source.seek(max(0, total - MAX_LOG_BYTES))
            log = source.read(MAX_LOG_BYTES).decode("utf-8", errors="replace")
    except OSError:
        print("Terraform apply failed; local diagnostic log could not be read.")
        return 0
    print(summarize(log))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
