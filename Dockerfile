FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies including curl and ca-certificates for cosign
RUN apt-get update && apt-get install -y \
    openssl \
    curl \
    ca-certificates \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Cosign binary
RUN wget -O /tmp/cosign "https://github.com/sigstore/cosign/releases/download/v2.2.4/cosign-linux-amd64" \
    && chmod +x /tmp/cosign \
    && mv /tmp/cosign /usr/local/bin/cosign

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY webhook.py image_attestation.py policy_config.py .

# Create necessary directories
RUN mkdir -p /certs /tmp /etc/attestation

# Create non-root user
RUN groupadd -r webhook && useradd -r -g webhook webhook
RUN chown -R webhook:webhook /app /certs /tmp /etc/attestation
USER webhook

# Expose port
EXPOSE 8443

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('https://localhost:8443/health', verify=False)" || exit 1

# Run the application
CMD ["python", "webhook.py"]
