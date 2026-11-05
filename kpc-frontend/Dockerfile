# Imagem de produção do frontend (deploy/docker-compose.yml): compila o
# React e serve os arquivos com o Caddy, que também repassa /api ao backend
# e cuida do HTTPS (configuração em deploy/Caddyfile).
# Para desenvolvimento com Docker, use launcher/Dockerfile.
FROM node:20-slim AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY vite.mvvm.config.js ./
COPY src-mvvm ./src-mvvm

# Endereço da API visto pelo navegador: /api no mesmo site
ARG VITE_API_BASE_URL=/api
RUN VITE_API_BASE_URL="$VITE_API_BASE_URL" npm run build:mvvm

FROM caddy:2.8.4-alpine

COPY --from=build /app/dist-mvvm /srv
