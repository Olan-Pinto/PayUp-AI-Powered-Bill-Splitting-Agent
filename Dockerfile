# Base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy files
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose Cloud Run port
EXPOSE 8080

# Use PORT environment variable
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}