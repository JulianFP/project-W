FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends git curl

RUN pip install gunicorn

COPY . .

RUN --mount=source=.git,target=.git,type=bind \
    pip install --no-cache-dir -e .

CMD ["gunicorn", "--bind", "backend:8080", "project_W:create_app()"]

HEALTHCHECK CMD curl -f http://backend:8080/api/about || exit 1
