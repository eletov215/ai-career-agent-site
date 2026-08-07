#!/usr/bin/env python3
"""Start Gunicorn and the external sync worker as sibling processes on Render.

Render free web services cannot provision a free background worker. This small
supervisor keeps the worker outside Gunicorn while sharing the same container.
VPS/Docker deployments run the same worker as an independent Compose service.
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
