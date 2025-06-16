# ──────────────────────────────────────────────────────────────
# Digital Picture Frame  –  slim, single-stage image
# - Installs Python wheels directly in the final layer
# - Uses a tiny static FFmpeg build (no apt caches, no duplicate libs)
# ──────────────────────────────────────────────────────────────
FROM python:3.12-slim

# ---------- install ffmpeg / ffprobe (static build ~15 MB) -----
RUN set -eux; \
    apt-get update && apt-get install -y curl ca-certificates --no-install-recommends && \
    curl -L -o /usr/local/bin/ffmpeg  https://github.com/FFmpeg/FFmpeg/releases/download/n6.1.1/ffmpeg-n6.1.1-linux64 && \
    curl -L -o /usr/local/bin/ffprobe https://github.com/FFmpeg/FFmpeg/releases/download/n6.1.1/ffprobe-n6.1.1-linux64 && \
    chmod +x /usr/local/bin/ffmpeg /usr/local/bin/ffprobe && \
    apt-get purge -y curl && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# ---------- set workdir & copy only what we need ---------------
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY templates/ templates/
COPY static/ static/

# ---------- environment & startup ------------------------------
ENV FLASK_APP=app/app.py \
    FLASK_RUN_HOST=0.0.0.0 \
    FLASK_RUN_PORT=8080

EXPOSE 8080
CMD ["waitress-serve", "--host=0.0.0.0", "--port=8080", "app.app:app"]
