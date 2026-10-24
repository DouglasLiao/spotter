# Optional single-service Docker image; Vercel uses vercel.json with native runtimes.
FROM node:24-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ENV VITE_API_BASE_URL=/api
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBUG=False \
    FRONTEND_DIST=/app/frontend_dist \
    DATABASE_PATH=/app/data/db.sqlite3
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install -r requirements.txt
RUN groupadd --gid 10001 spotter \
    && useradd --uid 10001 --gid spotter --no-create-home spotter \
    && mkdir -p /app/data /app/staticfiles \
    && chown -R spotter:spotter /app
COPY --chown=spotter:spotter backend/ ./
COPY --from=frontend-build --chown=spotter:spotter /frontend/dist /app/frontend_dist
USER spotter
EXPOSE 10000
ENTRYPOINT ["sh", "/app/docker-entrypoint.sh"]
CMD ["sh", "-c", "exec gunicorn core.wsgi:application --bind 0.0.0.0:${PORT:-10000} --workers 2 --threads 4 --timeout 180 --access-logfile - --error-logfile -"]
