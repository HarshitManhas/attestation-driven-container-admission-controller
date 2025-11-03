#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CERT_DIR="$PROJECT_DIR/certs"

SERVICE_NAME="attestation-admission-controller"
NAMESPACE="default"
CN="$SERVICE_NAME.$NAMESPACE.svc"

mkdir -p "$CERT_DIR"

# 1) Create a CA (CA:TRUE)
cat > "$CERT_DIR/ca.conf" <<'EOF'
[ req ]
distinguished_name = dn
x509_extensions = v3_ca
prompt = no

[ dn ]
CN = attestation-admission-controller-ca

[ v3_ca ]
basicConstraints = critical, CA:TRUE
keyUsage = critical, keyCertSign, cRLSign
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always,issuer
EOF

openssl genrsa -out "$CERT_DIR/ca.key" 4096
openssl req -x509 -new -key "$CERT_DIR/ca.key" -days 3650 \
  -out "$CERT_DIR/ca.crt" -config "$CERT_DIR/ca.conf" -extensions v3_ca

# 2) Create server key + CSR with SANs (CA:FALSE)
cat > "$CERT_DIR/csr.conf" <<EOF
[ req ]
req_extensions = v3_req
distinguished_name = dn
prompt = no

[ dn ]
CN = $CN

[ v3_req ]
basicConstraints = CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[ alt_names ]
DNS.1 = $SERVICE_NAME
DNS.2 = $SERVICE_NAME.$NAMESPACE
DNS.3 = $SERVICE_NAME.$NAMESPACE.svc
DNS.4 = $SERVICE_NAME.$NAMESPACE.svc.cluster.local
EOF

openssl genrsa -out "$CERT_DIR/tls.key" 2048
openssl req -new -key "$CERT_DIR/tls.key" -out "$CERT_DIR/tls.csr" -config "$CERT_DIR/csr.conf"

# 3) Sign server cert with the CA
openssl x509 -req -in "$CERT_DIR/tls.csr" -CA "$CERT_DIR/ca.crt" -CAkey "$CERT_DIR/ca.key" -CAcreateserial \
  -out "$CERT_DIR/tls.crt" -days 365 -extfile "$CERT_DIR/csr.conf" -extensions v3_req

# 4) Prepare Kubernetes secret and CA bundle
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

cp "$CERT_DIR/ca.crt" "$CERT_DIR/ca-bundle.crt"
echo "CA_BUNDLE:"
base64 -w 0 < "$CERT_DIR/ca-bundle.crt"
echo
echo "Apply secret with: kubectl apply -f $CERT_DIR/webhook-certs.yaml"