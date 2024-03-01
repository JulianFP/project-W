FROM python:3.11

LABEL org.opencontainers.image.source=https://github.com/JulianFP/project-W
LABEL org.opencontainers.image.description="Project-W backend production image"
LABEL org.opencontainers.image.licenses=MIT

WORKDIR /app

COPY . .

RUN pip install .

RUN pip install gunicorn

CMD ["gunicorn", "--bind", "backend:8080", "project_W:create_app()"]
