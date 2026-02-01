FROM python:3.12-slim

# Set timezone
ENV TZ=Europe/Madrid
RUN apt-get update && apt-get install -y tzdata procps && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Ensure entrypoint is executable
RUN chmod +x scripts/docker_entrypoint.sh

# Environment variables
ENV PYTHONUNBUFFERED=1

CMD ["./scripts/docker_entrypoint.sh"]
