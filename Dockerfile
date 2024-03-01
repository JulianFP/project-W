FROM node:20-slim AS builder

ARG BACKEND_BASE_URL=""

LABEL org.opencontainers.image.source=https://github.com/JulianFP/project-W-frontend
LABEL org.opencontainers.image.description="Project-W frontend production image"
LABEL org.opencontainers.image.licenses=MIT

WORKDIR /app

RUN npm install -g pnpm

COPY package*.json ./

RUN pnpm install

COPY . .

RUN VITE_BACKEND_BASE_URL=$BACKEND_BASE_URL pnpm build

FROM nginx

COPY --from=builder /app/dist /usr/share/nginx/html

COPY nginx.conf /etc/nginx/conf.d/default.conf
