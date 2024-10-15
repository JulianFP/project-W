FROM node:20-slim AS builder

ARG BACKEND_BASE_URL=""

LABEL org.opencontainers.image.source=https://github.com/JulianFP/project-W-frontend
LABEL org.opencontainers.image.description="Project-W frontend production image"
LABEL org.opencontainers.image.licenses=AGPL-3.0-only

WORKDIR /app

COPY . .

RUN npm install -g pnpm

RUN pnpm install

RUN VITE_BACKEND_BASE_URL=$BACKEND_BASE_URL pnpm build

FROM nginx:alpine-slim

ENV NGINX_CONFIG "ssl"

COPY --from=builder /app/dist /usr/share/nginx/html

COPY Docker/ /NginxConfigs

CMD ln -sfT /NginxConfigs/nginx_${NGINX_CONFIG}.conf /etc/nginx/conf.d/default.conf && nginx -g "daemon off;"
