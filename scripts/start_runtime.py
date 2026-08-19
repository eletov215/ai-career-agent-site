#!/usr/bin/env python3
"""Start Gunicorn and durable background workers as sibling processes on Render.

Render free web services cannot provision separate free background workers. This
supervisor keeps Trudvsem sync and privacy retention outside Gunicorn while
sharing the same container. VPS/Docker deployments can run both workers as
independent Compose services.
"""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("runtime_supervisor")
_CHILDREN: list[subprocess.Popen] = []
_STOPPING = False


def _enabled(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _terminate_children(signum=None, _frame=None) -> None:  # noqa: ANN001
    global _STOPPING
    _STOPPING = True
    for child in _CHILDREN:
        if child.poll() is None:
            try:
                child.send_signal(signum or signal.SIGTERM)
            except ProcessLookupError:
                pass


def _spawn(command: list[str], name: str) -> subprocess.Popen:
    logger.info("Starting %s: %s", name, " ".join(command))
    child = subprocess.Popen(command)
    _CHILDREN.append(child)
    return child


def main() -> int:
    for signal_name in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signal_name, _terminate_children)

    worker = None
    if _enabled("TRUDVSEM_SYNC_ENABLED", default=True):
        worker = _spawn(
            [sys.executable, "scripts/trudvsem_sync_worker.py"],
            "trudvsem-worker",
        )

    privacy_worker = None
    if _enabled("PRIVACY_CLEANUP_ENABLED", default=True):
        privacy_worker = _spawn(
            [sys.executable, "scripts/privacy_cleanup_worker.py"],
            "privacy-cleanup-worker",
        )

    gunicorn = _spawn(
        [
            sys.executable,
            "-m",
            "gunicorn",
            "--config",
            "infra/gunicorn.conf.py",
            "app:app",
        ],
        "gunicorn",
    )

    try:
        while not _STOPPING:
            gunicorn_code = gunicorn.poll()
            if gunicorn_code is not None:
                logger.error("Gunicorn exited with code %s", gunicorn_code)
                return int(gunicorn_code)

            if worker is not None and worker.poll() is not None:
                worker_code = worker.returncode
                logger.error(
                    "Trudvsem worker exited with code %s; restarting in 5 seconds",
                    worker_code,
                )
                time.sleep(5)
                if not _STOPPING:
                    worker = _spawn(
                        [sys.executable, "scripts/trudvsem_sync_worker.py"],
                        "trudvsem-worker",
                    )

            if privacy_worker is not None and privacy_worker.poll() is not None:
                privacy_code = privacy_worker.returncode
                logger.error(
                    "Privacy cleanup worker exited with code %s; restarting in 5 seconds",
                    privacy_code,
                )
                time.sleep(5)
                if not _STOPPING:
                    privacy_worker = _spawn(
                        [sys.executable, "scripts/privacy_cleanup_worker.py"],
                        "privacy-cleanup-worker",
                    )
            time.sleep(1)
    finally:
        _terminate_children()
        deadline = time.monotonic() + 15
        for child in _CHILDREN:
            if child.poll() is None:
                timeout = max(0.1, deadline - time.monotonic())
                try:
                    child.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    child.kill()
        for child in _CHILDREN:
            if child.poll() is None:
                child.kill()

    return 0


if __name__ == "__main__":
    sys.exit(main())
