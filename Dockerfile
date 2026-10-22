FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --create-home --uid 10001 arbiter \
    && mkdir -p /app/logs /app/var \
    && chown -R arbiter:arbiter /app/logs /app/var

USER arbiter

EXPOSE 8000 8501

HEALTHCHECK --interval=5s --timeout=5s --start-period=30s --retries=12 \
    CMD python -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

CMD ["python", "run.py", "serve"]
