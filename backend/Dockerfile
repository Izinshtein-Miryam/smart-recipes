FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv

COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir .
COPY alembic.ini ./
COPY alembic ./alembic

RUN useradd --system --uid 10001 app && mkdir -p /srv/storage && chown app /srv/storage
USER app
ENV STORAGE_DIR=/srv/storage
EXPOSE 8000

# Migrations run on start; uvicorn trusts the proxy headers so the rate limit sees real client IPs.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
