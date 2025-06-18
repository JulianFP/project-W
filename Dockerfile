ARG PYTHON_VERSION=3.13

FROM node:24-slim AS builder

WORKDIR /frontend-code

RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates

RUN npm install -g pnpm

ARG FRONTEND_BRANCH_NAME=main

RUN git clone -b ${FRONTEND_BRANCH_NAME} https://github.com/JulianFP/project-W-frontend.git .

RUN pnpm install

RUN pnpm build

FROM python:${PYTHON_VERSION}-slim

# gcc, libldap and libsas are required to compile bonsai (the ldap library we use) since it doesn't have any wheels on pypi
RUN apt-get update && apt-get install -y --no-install-recommends git curl gcc libldap2-dev libsasl2-dev

COPY --from=builder /frontend-code/build /frontend

WORKDIR /backend

COPY . .

RUN --mount=source=.git,target=.git,type=bind \
    pip install --no-cache-dir --upgrade -e .

CMD ["python", "-m", "project_W", "--root_static_files", "/frontend"]
