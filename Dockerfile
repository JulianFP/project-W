FROM python:3.11-slim

ARG PSEUDO_VERSION="0.0.1"

LABEL org.opencontainers.image.source=https://github.com/JulianFP/project-W
LABEL org.opencontainers.image.description="Project-W backend production image"
LABEL org.opencontainers.image.licenses=AGPL-3.0-only

WORKDIR /app

COPY . .

RUN SETUPTOOLS_SCM_PRETEND_VERSION=$PSEUDO_VERSION pip install .

RUN pip install gunicorn

CMD ["gunicorn", "--bind", "backend:8080", "project_W:create_app()"]
