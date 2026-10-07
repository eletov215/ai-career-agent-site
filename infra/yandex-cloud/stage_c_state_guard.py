#!/usr/bin/env python3
"""Fail closed if a previous HOST-001 Stage C Terraform state still owns resources."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from xml.etree import ElementTree

ENDPOINT = "https://storage.yandexcloud.net"
HOST = "storage.yandexcloud.net"
REGION = "ru-central1"
SERVICE = "s3"
PREFIX = "host001/stage-c"


class GuardError(RuntimeError):
    pass


def _hmac(key: bytes, value: str) -> bytes:
    return hmac.new(key, value.encode("utf-8"), hashlib.sha256).digest()


def _quote(value: str) -> str:
    return quote(value, safe="-_.~")


def _canonical_query(params: list[tuple[str, str]]) -> str:
    return "&".join(
        f"{_quote(key)}={_quote(value)}"
        for key, value in sorted(params, key=lambda item: (item[0], item[1]))
    )


def _signing_key(secret_key: str, date_stamp: str) -> bytes:
    key = _hmac(("AWS4" + secret_key).encode("utf-8"), date_stamp)
    key = _hmac(key, REGION)
    key = _hmac(key, SERVICE)
    return _hmac(key, "aws4_request")


def _request(
    *,
    method: str,
    bucket: str,
    key: str = "",
    query: list[tuple[str, str]] | None = None,
) -> tuple[int, bytes]:
    access_key = (os.getenv("AWS_ACCESS_KEY_ID") or "").strip()
    secret_key = (os.getenv("AWS_SECRET_ACCESS_KEY") or "").strip()
    if not access_key or not secret_key:
        raise GuardError("Object Storage access credentials are required.")

    now = datetime.now(timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")
    body = b""
    payload_hash = hashlib.sha256(body).hexdigest()

    canonical_uri = "/" + quote(bucket, safe="")
    if key:
        canonical_uri += "/" + quote(key, safe="/-_.~")
    params = query or []
    canonical_query = _canonical_query(params)
    canonical_headers = (
        f"host:{HOST}\n"
        f"x-amz-content-sha256:{payload_hash}\n"
        f"x-amz-date:{amz_date}\n"
    )
    signed_headers = "host;x-amz-content-sha256;x-amz-date"
    canonical_request = "\n".join(
        (
            method,
            canonical_uri,
            canonical_query,
            canonical_headers,
            signed_headers,
            payload_hash,
        )
    )

    scope = f"{date_stamp}/{REGION}/{SERVICE}/aws4_request"
    string_to_sign = "\n".join(
        (
            "AWS4-HMAC-SHA256",
            amz_date,
            scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        )
    )
    signature = hmac.new(
        _signing_key(secret_key, date_stamp),
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    authorization = (
        f"AWS4-HMAC-SHA256 Credential={access_key}/{scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )

    url = ENDPOINT + canonical_uri
    if canonical_query:
        url += "?" + canonical_query

    request = Request(
        url,
        method=method,
        headers={
            "Authorization": authorization,
            "Host": HOST,
            "x-amz-content-sha256": payload_hash,
            "x-amz-date": amz_date,
        },
    )
    try:
        with urlopen(request, timeout=20) as response:
            return response.status, response.read()
    except HTTPError as exc:
        return exc.code, exc.read()
    except URLError as exc:
        raise GuardError(f"Object Storage request failed: {exc.reason}") from exc


def _xml_text(node: ElementTree.Element, local_name: str) -> str | None:
    for child in node.iter():
        if child.tag.rsplit("}", 1)[-1] == local_name:
            return child.text
    return None


def list_state_keys(bucket: str) -> list[str]:
    token: str | None = None
    keys: list[str] = []
    while True:
        query = [("list-type", "2"), ("prefix", PREFIX)]
        if token:
            query.append(("continuation-token", token))
        status, body = _request(method="GET", bucket=bucket, query=query)
        if status != 200:
            raise GuardError(f"Unable to list Stage C state objects (HTTP {status}).")

        try:
            root = ElementTree.fromstring(body)
        except ElementTree.ParseError as exc:
            raise GuardError("Object Storage returned invalid ListObjects XML.") from exc

        for contents in root.iter():
            if contents.tag.rsplit("}", 1)[-1] != "Contents":
                continue
            key = _xml_text(contents, "Key")
            if key and key.endswith(".tfstate"):
                keys.append(key)

        truncated = (_xml_text(root, "IsTruncated") or "").lower() == "true"
        if not truncated:
            break
        token = _xml_text(root, "NextContinuationToken")
        if not token:
            raise GuardError("Object Storage pagination was truncated without a token.")

    return sorted(set(keys))


def managed_resource_count(bucket: str, key: str) -> int:
    status, body = _request(method="GET", bucket=bucket, key=key)
    if status == 404:
        return 0
    if status != 200:
        raise GuardError(f"Unable to read Terraform state {key!r} (HTTP {status}).")

    try:
        state = json.loads(body)
    except json.JSONDecodeError as exc:
        raise GuardError(f"Terraform state {key!r} is not valid JSON.") from exc

    count = 0
    for resource in state.get("resources", []):
        if resource.get("mode", "managed") != "managed":
            continue
        instances = resource.get("instances") or []
        count += len(instances)
    return count


def check_no_live_state(bucket: str) -> None:
    if not bucket or "/" in bucket:
        raise GuardError("A valid Object Storage bucket name is required.")

    live: list[tuple[str, int]] = []
    for key in list_state_keys(bucket):
        count = managed_resource_count(bucket, key)
        if count:
            live.append((key, count))

    if live:
        details = ", ".join(f"{key} ({count} managed)" for key, count in live)
        raise GuardError(
            "Refusing a new Stage C apply because durable Terraform state still "
            f"owns resources: {details}"
        )

    print("Stage C durable-state overlap guard: no managed resources found.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", required=True)
    args = parser.parse_args(argv)

    try:
        check_no_live_state(args.bucket.strip())
    except GuardError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
