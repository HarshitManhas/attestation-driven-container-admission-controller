# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Prerequisites

- Minikube installed and running (`minikube start`)
- kubectl configured for Minikube
- Docker installed
- OpenSSL installed

## Essential Commands

### Quick Start
```bash
# Deploy everything (builds image, generates certs, deploys to Kubernetes)
./scripts/deploy.sh

# Run comprehensive tests to verify deployment
./scripts/test.sh

# Clean up all resources when done
./scripts/cleanup.sh
```

### Development & Testing
```bash
# Build Docker image locally (uses Minikube's Docker daemon)
eval $(minikube docker-env)
docker build -t attestation-admission-controller:latest .

# View real-time webhook logs
kubectl logs -l app=attestation-admission-controller -f

# Test individual scenarios
kubectl apply -f tests/trusted-pod.yaml      # Should succeed
kubectl apply -f tests/untrusted-pod.yaml    # Should fail
kubectl apply -f tests/mixed-pod.yaml        # Should fail
kubectl apply -f tests/all-trusted-pod.yaml  # Should succeed

# Debug webhook endpoints
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

# Test a single scenario and clean up
kubectl apply -f tests/trusted-pod.yaml
kubectl delete pod trusted-nginx-pod

# Emergency webhook removal (if blocking all pods)
kubectl delete validatingwebhookconfigurations attestation-admission-controller
```

### Debugging Commands
```bash
# Check deployment status
kubectl get pods -l app=attestation-admission-controller
kubectl describe deployment attestation-admission-controller

# Check webhook configuration
kubectl get validatingwebhookconfigurations
kubectl describe validatingwebhookconfigurations attestation-admission-controller

# Check certificates
kubectl get secret webhook-certs -o yaml

# Regenerate certificates if needed
./scripts/generate-certs.sh
```

## Architecture Overview

This is a **Kubernetes ValidatingAdmissionWebhook** that implements container image attestation to ensure only trusted images can be deployed in a cluster. The system intercepts pod creation requests and validates them before admission.

### Core Components

**webhook.py** - Python Flask application (191 lines):
- `AdmissionController` class contains all validation logic
- Three main endpoints: `/validate` (admission logic), `/health` (status), `/trusted-images` (debugging)
- Handles both regular containers and init containers in pod specs
- Uses structured logging for debugging
- Runs on port 8443 with TLS encryption

**Certificate Management** - Self-signed TLS certificates:
- Generated via `scripts/generate-certs.sh` using OpenSSL
- Creates CA certificate, server certificate, and key files
- CA bundle is base64-encoded and embedded in webhook configuration
- Certificates stored in `certs/` directory and deployed as Kubernetes secret

**Kubernetes Resources**:
- **Deployment**: Runs webhook as containerized service with security constraints
- **Service**: Exposes webhook on port 443 (mapped from container port 8443)
- **ValidatingAdmissionWebhook**: Intercepts pod CREATE operations
- **Secret**: Contains TLS certificates for webhook communication

### Request Flow

1. User submits pod manifest (`kubectl apply -f pod.yaml`)
2. Kubernetes API server receives request
3. ValidatingAdmissionWebhook intercepts, sends AdmissionReview to webhook service
4. Flask app extracts pod spec, validates all container images against `TRUSTED_IMAGES` set
5. Returns AdmissionResponse with `allowed: true/false` and explanatory message
6. Kubernetes creates or rejects pod based on response

### Key Implementation Details

**Image Processing**: The `is_image_trusted()` method normalizes image names by stripping registry prefixes (e.g., `docker.io/library/nginx:latest` becomes `nginx:latest`).

**Comprehensive Validation**: The `extract_images_from_pod()` method checks both `containers` and `initContainers` arrays in pod specifications.

**Error Handling**: Uses `failurePolicy: Fail` to deny pods if webhook is unavailable, ensuring security-first behavior. All exceptions are caught and result in pod denial.

**Security Configuration**: Webhook runs as non-root user, uses read-only filesystem, and has resource limits (128Mi memory, 100m CPU).

## Configuration

### Trusted Images List
The `TRUSTED_IMAGES` set in `webhook.py` (lines 20-28) contains the allowlist:
```python
TRUSTED_IMAGES = {
    "nginx:1.21", "nginx:latest", 
    "alpine:3.14", "alpine:latest",
    "python:3.9-slim", "busybox:latest",
    "hello-world:latest"
}
```

To modify trusted images:
1. Edit the `TRUSTED_IMAGES` set in `webhook.py`
2. Redeploy: `./scripts/cleanup.sh && ./scripts/deploy.sh`

**Note**: This is a mock implementation for demonstration. Production systems should integrate with actual attestation services (Sigstore, Notary, etc.).

### Webhook Configuration
- **Namespace exclusions**: Skips `kube-system`, `kube-public`, `kube-node-lease` namespaces
- **Operations**: Only intercepts `CREATE` operations on pods
- **Failure policy**: `Fail` (denies pods if webhook unavailable)
- **Admission review versions**: Supports both `v1` and `v1beta1`

### Container Security
- Runs as non-root user `webhook:webhook` (UID/GID 1000)
- Read-only root filesystem
- Resource limits: 128Mi memory, 100m CPU
- Health check endpoint on `/health`

### Development Environment
- **Minikube**: Required (uses `imagePullPolicy: Never` for local images)
- **Docker environment**: Must switch to Minikube's daemon with `eval $(minikube docker-env)`
- **Port forwarding**: Use `kubectl port-forward` to access webhook endpoints

## Testing Strategy

The test suite (`scripts/test.sh`) validates admission control logic with four scenarios:

| Test File | Images | Expected Result | Purpose |
|-----------|--------|-----------------|---------|
| `trusted-pod.yaml` | `nginx:latest` | ✅ ALLOWED | Single trusted image |
| `untrusted-pod.yaml` | `redis:6.2` | ❌ DENIED | Single untrusted image |
| `mixed-pod.yaml` | `nginx:latest` + `mysql:8.0` | ❌ DENIED | Mixed trusted/untrusted |
| `all-trusted-pod.yaml` | `busybox:latest` + `nginx:latest` + `alpine:latest` | ✅ ALLOWED | Multiple trusted (with init containers) |

The test script automatically:
- Waits for webhook deployment to be ready
- Tests each scenario and validates expected outcomes
- Cleans up resources after successful tests
- Shows recent webhook logs for debugging
- Tests webhook health and trusted-images endpoints

## Key Files and Structure

```
attestation-admission-controller/
├── webhook.py              # Main Flask application (191 lines)
├── requirements.txt        # Python dependencies (Flask, gunicorn, sigstore, etc.)
├── Dockerfile             # Multi-stage build with security hardening
├── scripts/
│   ├── deploy.sh          # Full deployment automation
│   ├── test.sh            # Comprehensive test suite
│   ├── cleanup.sh         # Resource cleanup
│   └── generate-certs.sh  # SSL certificate generation
├── k8s/
│   ├── deployment.yaml    # Webhook deployment spec
│   ├── service.yaml       # Service configuration
│   └── webhook-configuration.yaml # ValidatingAdmissionWebhook template
├── tests/
│   └── *.yaml             # Test pod specifications
├── certs/                 # Generated certificates (created during deployment)
└── WARP.md               # This file
```

## Development Notes

### Debugging Workflow
1. Enable verbose logging: Change line 14 in `webhook.py` to `logging.basicConfig(level=logging.DEBUG)`
2. Monitor real-time logs: `kubectl logs -l app=attestation-admission-controller -f`
3. Test endpoints: `/health` (status check), `/trusted-images` (current allowlist)
4. Use port-forwarding for direct webhook access: `kubectl port-forward svc/attestation-admission-controller 8443:443`

### Code Modification Workflow
This project uses Minikube's local Docker registry for rapid iteration:
1. Make changes to `webhook.py`
2. Switch Docker context: `eval $(minikube docker-env)`
3. Rebuild image: `docker build -t attestation-admission-controller:latest .`
4. Restart deployment: `kubectl rollout restart deployment/attestation-admission-controller`
5. Test changes: `kubectl apply -f tests/trusted-pod.yaml`

### Important Constraints
- **Minikube dependency**: Uses `imagePullPolicy: Never` requiring local image builds
- **Certificate lifecycle**: Certificates are generated per deployment cycle
- **Namespace exclusions**: System namespaces are excluded to prevent cluster lockout
- **Failure policy**: Webhook failures result in pod denial for security
