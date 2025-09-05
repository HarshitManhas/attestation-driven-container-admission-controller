#!/bin/bash

# Script to generate SSL certificates for the admission webhook
# This creates a self-signed certificate that Kubernetes can trust

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CERT_DIR="$PROJECT_DIR/certs"

# Service and namespace details
SERVICE_NAME="attestation-admission-controller"
NAMESPACE="default"

# Create certs directory if it doesn't exist
mkdir -p "$CERT_DIR"

echo "Generating certificates for $SERVICE_NAME in namespace $NAMESPACE..."

# Generate private key
openssl genrsa -out "$CERT_DIR/tls.key" 2048

# Generate certificate signing request
cat > "$CERT_DIR/csr.conf" <<EOF
[req]
req_extensions = v3_req
distinguished_name = req_distinguished_name
[req_distinguished_name]
[v3_req]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
subjectAltName = @alt_names
[alt_names]
DNS.1 = $SERVICE_NAME
DNS.2 = $SERVICE_NAME.$NAMESPACE
DNS.3 = $SERVICE_NAME.$NAMESPACE.svc
DNS.4 = $SERVICE_NAME.$NAMESPACE.svc.cluster.local
EOF

# Generate certificate signing request
openssl req -new -key "$CERT_DIR/tls.key" -out "$CERT_DIR/tls.csr" -config "$CERT_DIR/csr.conf" -subj "/CN=$SERVICE_NAME.$NAMESPACE.svc"

# Generate self-signed certificate
openssl x509 -req -in "$CERT_DIR/tls.csr" -signkey "$CERT_DIR/tls.key" -out "$CERT_DIR/tls.crt" -days 365 -extensions v3_req -extfile "$CERT_DIR/csr.conf"

# Generate CA bundle (for webhook configuration)
cp "$CERT_DIR/tls.crt" "$CERT_DIR/ca-bundle.crt"

# Create Kubernetes secret YAML
cat > "$CERT_DIR/webhook-certs.yaml" <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: webhook-certs
  namespace: $NAMESPACE
type: Opaque
data:
  tls.crt: $(base64 -w 0 < "$CERT_DIR/tls.crt")
  tls.key: $(base64 -w 0 < "$CERT_DIR/tls.key")
EOF

# Get the CA bundle for webhook configuration
CA_BUNDLE=$(base64 -w 0 < "$CERT_DIR/ca-bundle.crt")

echo "Certificates generated successfully!"
echo "Files created:"
echo "  - $CERT_DIR/tls.key (private key)"
echo "  - $CERT_DIR/tls.crt (certificate)"
echo "  - $CERT_DIR/ca-bundle.crt (CA bundle)"
echo "  - $CERT_DIR/webhook-certs.yaml (Kubernetes secret)"
echo ""
echo "CA Bundle for webhook configuration:"
echo "$CA_BUNDLE"
echo ""
echo "You can now deploy the certificates with:"
echo "kubectl apply -f $CERT_DIR/webhook-certs.yaml"
