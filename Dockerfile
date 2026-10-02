# Production Container Definition
FROM python:3.11-alpine

WORKDIR /app

COPY src/ /app/src/
COPY tests/ /app/tests/
COPY README.md /app/README.md

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health')" || exit 1

ENTRYPOINT ["python", "src/server.py", "8080"]
