FROM python:3.11-slim

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY src/ ./src/
COPY data/ ./data/
COPY tests/ ./tests/
COPY scripts/ ./scripts/
COPY README.md ./

EXPOSE 8000

# Default entrypoint runs the OpenAI proxy API & Telemetry Visualizer
CMD ["python", "src/server.py"]
