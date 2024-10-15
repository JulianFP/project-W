FROM python:3.12-slim

LABEL org.opencontainers.image.source=https://github.com/JulianFP/project-W
LABEL org.opencontainers.image.description="Project-W backend production image"
LABEL org.opencontainers.image.licenses=AGPL-3.0-only

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends git curl

RUN pip install gunicorn

COPY . .

RUN pip install .

CMD ["gunicorn", "--bind", "backend:8080", "project_W:create_app()"]

HEALTHCHECK CMD curl -f http://backend:8080/api/about || exit 1
