FROM python:3.10-slim

WORKDIR /app

# Install system dependencies if needed (e.g. for building packages)
# RUN apt-get update && apt-get install -y build-essential

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Default command (can be overridden in docker-compose)
CMD ["python", "poly_client.py"]
