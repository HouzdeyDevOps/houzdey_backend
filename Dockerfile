FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# ffmpeg (and ffprobe) are used to watermark uploaded videos.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# The app writes log files to ./logs, so the non-root user must own it.
RUN useradd --create-home appuser \
    && mkdir -p /app/logs \
    && chown -R appuser /app/logs
USER appuser

EXPOSE 8000

# Render sets $PORT; fall back to 8000 for local runs.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
