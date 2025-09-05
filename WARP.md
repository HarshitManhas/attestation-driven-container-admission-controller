# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Common Commands

### Development & Deployment
```bash
# Full deployment (builds image, generates certs, deploys to Kubernetes)
./scripts/deploy.sh

# Run comprehensive tests
./scripts/test.sh

# Clean up all resources
./scripts/cleanup.sh

# Build Docker image locally (uses Minikube's Docker daemon)
eval $(minikube docker-env)
docker build -t attestation-admission-controller:latest .

# Generate SSL certificates only
./scripts/generate-certs.sh

# View real-time webhook logs
kubectl logs -l app=attestation-admission-controller -f

# Test individual pods
kubectl apply -f tests/trusted-pod.yaml      # Should succeed
kubectl apply -f tests/untrusted-pod.yaml    # Should fail
kubectl apply -f tests/mixed-pod.yaml        # Should fail
kubectl apply -f tests/all-trusted-pod.yaml  # Should succeed

# Debug webhook health
kubectl port-forward svc/attestation-admission-controller 8443:443
curl -k https://localhost:8443/health
curl -k https://localhost:8443/trusted-images
```

### Development Workflow
```bash
# After making code changes to webhook.py
./scripts/cleanup.sh && ./scripts/deploy.sh

# Quick redeploy without full cleanup (faster iteration)
eval $(minikube docker-env)
docker build -t attestation-admission-controller:latest .
kubectl rollout restart deployment/attestation-admission-controller
kubectl rollout status deployment/attestation-admission-controller

# Test a single scenario
kubectl apply -f tests/trusted-pod.yaml
kubectl delete pod trusted-nginx-pod  # Clean up

# Emergency webhook removal (if blocking all pods)
kubectl delete validatingwebhookconfigurations attestation-admission-controller
```

## Architecture Overview

This is a **Kubernetes ValidatingAdmissionWebhook** that implements container image attestation. The system follows a webhook pattern where Kubernetes API server intercepts pod creation requests and validates them before admission.

### Core Components

**webhook.py** - The main Flask application that:
- Implements the admission controller logic in the `AdmissionController` class
- Validates pod specifications by extracting all container images (including init containers)
- Checks images against a configurable trusted images list
- Returns structured AdmissionReview responses to Kubernetes

**Certificate Management** - Self-signed TLS certificates for webhook communication:
- Generated via `scripts/generate-certs.sh`
- Includes proper SAN (Subject Alternative Names) for Kubernetes service discovery
- CA bundle embedded in ValidatingAdmissionWebhook configuration

**Kubernetes Integration**:
- Deployment runs webhook as a containerized service
- Service exposes webhook on port 8443 with HTTPS
- ValidatingAdmissionWebhook configuration intercepts pod CREATE operations
- Excludes system namespaces (kube-system, kube-public, etc.)

### Request Flow

1. User applies pod manifest (`kubectl apply -f pod.yaml`)
2. Kubernetes API server receives request
3. ValidatingAdmissionWebhook triggers, sends AdmissionReview to webhook service
4. Flask app extracts pod spec, validates all container images against trusted list
5. Returns AdmissionResponse with `allowed: true/false`
6. Kubernetes either creates or rejects the pod based on response

### Key Design Patterns

**Image Validation Logic**: The `is_image_trusted()` method handles registry prefixes by extracting the image name portion (e.g., `docker.io/library/nginx:latest` → `nginx:latest`).

**Comprehensive Container Checking**: The `extract_images_from_pod()` method validates both regular containers and init containers in pod specifications.

**Failure Handling**: Uses `failurePolicy: Fail` to deny pods if webhook is unavailable, ensuring security-first behavior.

## Configuration

### Trusted Images List
Located in `webhook.py` as the `TRUSTED_IMAGES` set. Currently includes common base images like nginx, alpine, python, busybox. This is a mock implementation - production systems should integrate with actual attestation services (Sigstore, Notary, etc.).

### Webhook Security Configuration
- Runs as non-root user (1000:1000)
- Read-only root filesystem
- Dropped capabilities
- Resource limits: 128Mi memory, 100m CPU max

### Environment Requirements
- **Minikube**: Required for local development (uses `imagePullPolicy: Never`)
- **Docker**: Must be configured to use Minikube's Docker daemon via `eval $(minikube docker-env)`
- **kubectl**: Configured to work with Minikube cluster

## Testing Strategy

The test suite (`scripts/test.sh`) validates four key scenarios:
1. **Trusted image**: Single container with allowed image (nginx:latest)
2. **Untrusted image**: Single container with blocked image (redis:6.2)
3. **Mixed images**: Multiple containers with both trusted/untrusted images
4. **All trusted**: Multiple containers and init containers, all trusted

Tests verify both positive (allowed) and negative (denied) cases, automatically cleaning up resources after each test.

## Development Notes

### Debugging
- Set `logging.basicConfig(level=logging.DEBUG)` in webhook.py for verbose logging
- Use `/health` and `/trusted-images` endpoints for webhook diagnostics
- Monitor webhook logs during pod creation attempts

### Local Development Workflow
This project is optimized for Minikube development. The deployment script handles Docker environment switching, certificate generation, and Kubernetes resource deployment in the correct order.

### Security Considerations
- Current implementation uses mock attestation (trusted images list)
- Self-signed certificates are suitable for development only
- Production deployment would require integration with actual image signing/attestation infrastructure
