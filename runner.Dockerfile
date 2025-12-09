FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update && apt-get install -y --no-install-recommends git

WORKDIR /app

COPY lib ./lib/

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=runner/uv.lock,target=runner/uv.lock \
    --mount=type=bind,source=runner/pyproject.toml,target=runner/pyproject.toml \
    uv sync --locked --no-install-project --no-editable --compile-bytecode --project runner

ADD . /app

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=.git,target=.git \
    uv sync --locked --no-editable --compile-bytecode --project runner --extra not_dummy

FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg

# Copy licensing information
COPY ./README.md ./LICENSE.md ./COPYING.md /app/

# Copy the environment, but not the source code
COPY --from=builder --chown=app:app /app/runner/.venv /app/runner/.venv

# See https://github.com/m-bain/whisperX/issues/1304#issuecomment-3599713003
ENV TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=true

CMD ["/app/runner/.venv/bin/project_W_runner"]
