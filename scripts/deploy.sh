#!/bin/bash

# Main deployment script for Attestation-Driven Container Admission Controller
# This script builds, deploys, and configures the admission controller on Minikube

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🚀 Deploying Attestation-Driven Container Admission Controller"
echo "=================================================="

# Check if minikube is running
echo "1. Checking Minikube status..."
if ! minikube status | grep -q "Running"; then
    echo "❌ Minikube is not running. Please start minikube first:"
    echo "   minikube start"
    exit 1
fi
echo "✅ Minikube is running"

# Switch to minikube docker environment
echo "2. Configuring Docker environment for Minikube..."
eval $(minikube docker-env)
echo "✅ Docker environment configured"

# Build the Docker image
echo "3. Building Docker image..."
cd "$PROJECT_DIR"
docker build -t attestation-admission-controller:latest .
echo "✅ Docker image built"

# Generate certificates
echo "4. Generating SSL certificates..."
"$SCRIPT_DIR/generate-certs.sh"
echo "✅ Certificates generated"

# Deploy the webhook certificates secret
echo "5. Deploying webhook certificates..."
kubectl apply -f "$PROJECT_DIR/certs/webhook-certs.yaml"
echo "✅ Certificates deployed"

# Deploy the webhook service and deployment
echo "6. Deploying webhook service and deployment..."
kubectl apply -f "$PROJECT_DIR/k8s/service.yaml"
kubectl apply -f "$PROJECT_DIR/k8s/deployment.yaml"

# Wait for deployment to be ready
echo "7. Waiting for deployment to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/attestation-admission-controller
echo "✅ Deployment is ready"

# Update webhook configuration with the correct CA bundle
echo "8. Configuring ValidatingAdmissionWebhook..."
CA_BUNDLE=$(base64 -w 0 < "$PROJECT_DIR/certs/ca-bundle.crt")

# Create temporary webhook configuration with actual CA bundle
cat > "$PROJECT_DIR/k8s/webhook-configuration-temp.yaml" <<EOF
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingWebhookConfiguration
metadata:
  name: attestation-admission-controller
webhooks:
  - name: attestation.admission.controller
    clientConfig:
      service:
        name: attestation-admission-controller
        namespace: default
        path: "/validate"
      caBundle: $CA_BUNDLE
    rules:
    - operations: ["CREATE"]
      apiGroups: [""]
      apiVersions: ["v1"]
      resources: ["pods"]
    admissionReviewVersions: ["v1", "v1beta1"]
    sideEffects: None
    failurePolicy: Fail
    namespaceSelector:
      matchExpressions:
      - key: name
        operator: NotIn
        values: 
        - kube-system
        - kube-public
        - kube-node-lease
EOF

kubectl apply -f "$PROJECT_DIR/k8s/webhook-configuration-temp.yaml"
rm "$PROJECT_DIR/k8s/webhook-configuration-temp.yaml"
echo "✅ ValidatingAdmissionWebhook configured"

echo ""
echo "🎉 Deployment completed successfully!"
echo ""
echo "📋 Next steps:"
echo "   1. Test with trusted image:   kubectl apply -f tests/trusted-pod.yaml"
echo "   2. Test with untrusted image: kubectl apply -f tests/untrusted-pod.yaml"
echo "   3. View webhook logs:         kubectl logs -l app=attestation-admission-controller -f"
echo "   4. Check webhook health:      kubectl port-forward svc/attestation-admission-controller 8443:443"
echo "                                 curl -k https://localhost:8443/health"
echo ""
echo "🔍 Troubleshooting:"
echo "   - View pod status:    kubectl get pods -l app=attestation-admission-controller"
echo "   - View webhook config: kubectl get validatingwebhookconfigurations"
echo "   - Delete webhook:     kubectl delete validatingwebhookconfigurations attestation-admission-controller"
