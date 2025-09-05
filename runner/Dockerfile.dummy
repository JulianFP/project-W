#to use the same image as in normal runner
FROM python:3.12-slim-bullseye

RUN apt-get update && apt-get install -y --no-install-recommends git

WORKDIR /runner

COPY ./runner .

RUN --mount=source=./runner/.git,target=.git,type=bind \
    pip install --no-cache-dir -e .

CMD ["python", "-m", "project_W_runner", "--dummy"]
