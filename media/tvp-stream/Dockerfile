FROM python:3.13-slim

ARG STREAMLINK_VERSION=8.5.0

RUN apt-get update \
    && apt-get install --yes --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir "streamlink==${STREAMLINK_VERSION}" \
    && useradd --create-home --uid 10001 streamlink

COPY --chown=streamlink:streamlink server.py /app/server.py

USER streamlink
WORKDIR /app

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=3)"]

CMD ["python", "/app/server.py"]
