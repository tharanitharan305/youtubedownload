# Dockerfile
FROM python:3.11-slim

# Install ffmpeg and other deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Expose port (Render provides PORT env var)
ENV PYTHONUNBUFFERED=1

# Use gunicorn for production
CMD exec gunicorn --bind 0.0.0.0:${PORT:-10000} app:app --workers 1 --threads 4
