FROM python:3.14-slim
WORKDIR /app

RUN groupadd -g 1000 app && useradd -m -u 1000 -g app app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY config/ config/

RUN mkdir -p /app/logs /app/data && chown -R app:app /app

USER app

HEALTHCHECK --interval=10m --timeout=10s --start-period=5m --retries=2 \
  CMD test -n "$(find /app/data/heartbeat -mmin -180 2>/dev/null)" || exit 1

CMD ["python", "-m", "src.main"]
