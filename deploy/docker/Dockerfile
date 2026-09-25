# syntax=docker/dockerfile:1

FROM node:22-alpine AS web
WORKDIR /web
COPY apps/web/package.json ./
RUN npm install
COPY apps/web ./
RUN npm run build

FROM python:3.12-slim AS api
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY eventlyra ./eventlyra
COPY services ./services
COPY apps ./apps
COPY packages ./packages
COPY --from=web /web/dist ./apps/web/dist
EXPOSE 8000
CMD ["python", "-m", "eventlyra", "--sessions-per-gpu", "2", "--sin-modelos", "--host", "0.0.0.0"]
