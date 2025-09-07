#to use the same image as in normal runner
FROM python:3.12-slim-bullseye AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update && apt-get install -y --no-install-recommends git

WORKDIR /app

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=runner/uv.lock,target=runner/uv.lock \
    --mount=type=bind,source=runner/pyproject.toml,target=runner/pyproject.toml \
    uv sync --locked --no-install-project --no-editable --compile-bytecode --project runner

ADD . /app

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=.git,target=.git \
    uv sync --locked --no-editable --compile-bytecode --project runner

FROM python:3.12-slim-bullseye

# Copy licensing information
COPY ./README.md ./LICENSE.md ./COPYING.md /app/

# Copy the environment, but not the source code
COPY --from=builder --chown=app:app /app/runner/.venv /app/runner/.venv

CMD ["/app/runner/.venv/bin/project_W_runner", "--dummy"]
