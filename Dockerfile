FROM node:20-slim AS builder

ARG BACKEND_BASE_URL=""

WORKDIR /app

COPY . .

RUN npm install -g pnpm

RUN pnpm install

RUN VITE_BACKEND_BASE_URL=$BACKEND_BASE_URL pnpm build

#to make container small
FROM nginx:alpine-slim

#for HEALTHCHECK
RUN apk --no-cache add curl

ENV NGINX_CONFIG="ssl"

COPY Docker/ /DockerHelpers

COPY --from=builder /app/dist /usr/share/nginx/html

ENTRYPOINT ["/DockerHelpers/entrypoint.sh"]

CMD ["nginx", "-g", "daemon off;"]

#-k needed for self-signed certificates
HEALTHCHECK CMD if [ $NGINX_CONFIG == "ssl" ]; then curl -kf https://localhost/; else curl -f http://localhost/; fi || exit 1
