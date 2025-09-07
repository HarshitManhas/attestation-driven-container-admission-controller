#!/bin/bash

# Cleanup script for the Attestation-Driven Container Admission Controller
# This script removes all resources created by the admission controller

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🧹 Cleaning up Attestation-Driven Container Admission Controller"
echo "=================================================="

# Remove ValidatingAdmissionWebhook (this is critical - do this first)
echo "1. Removing ValidatingAdmissionWebhook..."
kubectl delete validatingwebhookconfigurations attestation-admission-controller --ignore-not-found=true
echo " ValidatingAdmissionWebhook removed"

# Remove deployment
echo "2. Removing deployment..."
kubectl delete deployment attestation-admission-controller --ignore-not-found=true
echo " Deployment removed"

# Remove service
echo "3. Removing service..."
kubectl delete service attestation-admission-controller --ignore-not-found=true
echo " Service removed"

# Remove certificates secret
echo "4. Removing certificates secret..."
kubectl delete secret webhook-certs --ignore-not-found=true
echo " Certificates secret removed"

# Clean up any test pods that might be running
echo "5. Cleaning up test pods..."
kubectl delete pod trusted-nginx-pod --ignore-not-found=true
kubectl delete pod untrusted-redis-pod --ignore-not-found=true
kubectl delete pod mixed-containers-pod --ignore-not-found=true
kubectl delete pod all-trusted-pod --ignore-not-found=true
echo " Test pods cleaned up"

# Remove local certificates
echo "6. Cleaning up local certificates..."
rm -rf "$PROJECT_DIR/certs/"*.crt "$PROJECT_DIR/certs/"*.key "$PROJECT_DIR/certs/"*.csr "$PROJECT_DIR/certs/"*.conf "$PROJECT_DIR/certs/"*.yaml 2>/dev/null || true
echo " Local certificates cleaned up"

# Remove docker image (optional - from minikube docker)
echo "7. Removing Docker image..."
eval $(minikube docker-env) 2>/dev/null || true
docker rmi attestation-admission-controller:latest 2>/dev/null || true
echo " Docker image removed"

echo ""
echo "🎉 Cleanup completed successfully!"
echo ""
echo " What was removed:"
echo "   - ValidatingAdmissionWebhook configuration"
echo "   - Kubernetes deployment and service" 
echo "   - SSL certificates and secrets"
echo "   - Test pods"
echo "   - Local certificate files"
echo "   - Docker image"
echo ""
echo " To redeploy: ./scripts/deploy.sh"
