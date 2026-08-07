# syntax=docker/dockerfile:1.7

ARG PYTHON_IMAGE=python:3.11-slim-bookworm
ARG POSTGRES_IMAGE=postgres:17-bookworm

FROM ${PYTHON_IMAGE} AS app-builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

RUN python -m venv /opt/venv
COPY requirements.txt /build/requirements.txt
RUN /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install -r /build/requirements.txt

FROM ${PYTHON_IMAGE} AS runtime

ARG APP_UID=10001
ARG APP_GID=10001

ENV PATH=/opt/venv/bin:${PATH} \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000 \
    DATA_DIR=/var/lib/ai-career-agent \
    BACKUP_DIR=/var/backups/ai-career-agent

RUN groupadd --gid "${APP_GID}" app \
    && useradd --uid "${APP_UID}" --gid "${APP_GID}" --create-home --shell /usr/sbin/nologin app \
    && mkdir -p /app "${DATA_DIR}" "${BACKUP_DIR}" \
    && chown -R app:app /app "${DATA_DIR}" "${BACKUP_DIR}"

WORKDIR /app

COPY --from=app-builder /opt/venv /opt/venv
COPY --chown=app:app . /app

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.getenv('PORT', '8000') + '/health/live', timeout=4).read()" || exit 1

CMD ["python", "scripts/start_runtime.py"]

# OPS target: includes PostgreSQL 17 client tools so encrypted production
# backups can be created and restored from the same major version as the DB.
FROM ${POSTGRES_IMAGE} AS ops

ARG APP_UID=10001
ARG APP_GID=10001

ENV PATH=/opt/venv/bin:${PATH} \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DATA_DIR=/var/lib/ai-career-agent \
    BACKUP_DIR=/var/backups/ai-career-agent

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates \
       curl \
       python3 \
       python3-pip \
       python3-venv \
       tini \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN /opt/venv/bin/pip install -r /app/requirements.txt

COPY . /app

RUN groupadd --gid "${APP_GID}" app \
    && useradd --uid "${APP_UID}" --gid "${APP_GID}" --create-home --shell /usr/sbin/nologin app \
    && mkdir -p "${DATA_DIR}" "${BACKUP_DIR}" \
    && chown -R app:app /app "${DATA_DIR}" "${BACKUP_DIR}"

USER app
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "scripts/verify_backup.py", "--help"]
