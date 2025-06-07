FROM node:24-slim AS builder

WORKDIR /frontend-code

RUN npm install -g pnpm

ARG FRONTEND_BRANCH_NAME=main

RUN git clone -b ${BRANCH_NAME} https://github.com/JulianFP/project-W-frontend.git .

RUN pnpm install

RUN pnpm build

FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends git curl

COPY --from=builder /frontend-code/build /frontend

WORKDIR /backend

COPY . .

RUN --mount=source=.git,target=.git,type=bind \
    pip install --no-cache-dir --upgrade -e .

CMD ["python", "-m", "project_W", "--root_static_files", "/frontend"]

HEALTHCHECK CMD curl -f https://localhost/api/about || exit 1
