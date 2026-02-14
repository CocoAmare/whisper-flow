FROM python:3.11-slim-bookworm

# Install system dependencies
RUN apt-get update && apt-get install -y \
    portaudio19-dev \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Install whisper-flow package
RUN pip install whisperflow

CMD ["uvicorn", "whisperflow.fast_server:app", "--host", "0.0.0.0", "--port", "8181"]

