ARG PYTHON_VERSION=3.13

FROM python:${PYTHON_VERSION}-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# gcc, libldap and libsas are required to compile bonsai (the ldap library we use) since it doesn't have any wheels on pypi
RUN apt-get update && apt-get install -y --no-install-recommends git gcc libldap2-dev libsasl2-dev

WORKDIR /app

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=backend/uv.lock,target=backend/uv.lock \
    --mount=type=bind,source=backend/pyproject.toml,target=backend/pyproject.toml \
    uv sync --locked --no-install-project --no-editable --compile-bytecode --project backend

ADD . /app

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=.git,target=/app/.git \
    uv sync --locked --no-editable --compile-bytecode --project backend

FROM python:${PYTHON_VERSION}-slim

RUN apt-get update && apt-get install -y --no-install-recommends cron

# Copy licensing information
COPY ./README.md ./LICENSE.md ./COPYING.md /app/

# Copy the environment, but not the source code
COPY --from=builder --chown=app:app /app/backend/.venv /app/backend/.venv

RUN crontab -l | { cat; echo '0 0 * * * export $(/usr/bin/cat /proc/1/environ | /usr/bin/xargs --null) && /app/backend/.venv/bin/project_W --run_periodic_tasks > /proc/1/fd/1 2>&1'; } | crontab -

CMD ["cron", "-f"]
