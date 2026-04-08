
FROM python:3.11-slim

# System deps for OpenCV headless
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Pre-create logs dir with correct permissions
RUN mkdir -p /app/logs

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install opencv-python-headless --upgrade  # override with headless in Docker

COPY src/ ./src/
COPY vision_config.yaml .

CMD ["python", "src/main.py"]