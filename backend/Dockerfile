FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY requirements.txt ./
RUN pip install -r requirements.txt

RUN groupadd --gid 10001 spotter \
    && useradd --uid 10001 --gid spotter --no-create-home spotter \
    && mkdir -p /app/data /app/staticfiles \
    && chown -R spotter:spotter /app

COPY --chown=spotter:spotter . .
USER spotter
EXPOSE 8000
ENTRYPOINT ["sh", "/app/docker-entrypoint.sh"]
CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4", "--timeout", "180", "--access-logfile", "-", "--error-logfile", "-"]
