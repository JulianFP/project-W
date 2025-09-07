ARG PYTHON_VERSION=3.13

FROM node:24-slim AS frontend-builder

WORKDIR /frontend-code

RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates

RUN npm install -g pnpm

COPY ./frontend .

RUN pnpm install --frozen-lockfile

RUN --mount=source=.git,target=/.git,type=bind \
    pnpm build

FROM python:${PYTHON_VERSION}-slim AS backend-builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# gcc, libldap and libsas are required to compile bonsai (the ldap library we use) since it doesn't have any wheels on pypi
RUN apt-get update && apt-get install -y --no-install-recommends git gcc libldap2-dev libsasl2-dev

WORKDIR /app

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=backend/uv.lock,target=uv.lock \
    --mount=type=bind,source=backend/pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-editable --compile-bytecode

ADD ./backend /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=.git,target=/.git \
    ls -alh

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=.git,target=/.git \
    git status

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=.git,target=/.git \
    uv sync --locked --no-editable --compile-bytecode

FROM python:${PYTHON_VERSION}-slim

# curl to be able to perform health check
RUN apt-get update && apt-get install -y --no-install-recommends curl

# Copy licensing information
COPY ./README.md ./LICENSE.md ./COPYING.md /app/

# Copy the environment, but not the source code
COPY --from=backend-builder --chown=app:app /app/.venv /app/.venv

COPY --from=frontend-builder /frontend-code/build /app/frontend

CMD ["/app/.venv/bin/project_W", "--root_static_files", "/app/frontend"]
