FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    openssl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY webhook.py .

# Create certificates directory
RUN mkdir -p /certs

# Create non-root user
RUN groupadd -r webhook && useradd -r -g webhook webhook
RUN chown -R webhook:webhook /app /certs
USER webhook

# Expose port
EXPOSE 8443

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('https://localhost:8443/health', verify=False)" || exit 1

# Run the application
CMD ["python", "webhook.py"]
