# Attestation-Driven Container Admission Controller

A Kubernetes ValidatingAdmissionWebhook that implements container image attestation to ensure only trusted images can be deployed in your cluster.

## Architecture

```
+---------------------------+
| User applies pod.yaml     |
| (kubectl apply)           |
+-------------+-------------+
              |
              v
+---------------------------+
| Kubernetes API Server     |
| ValidatingWebhookConfig   |
+-------------+-------------+
              |
              v
+---------------------------+
| Admission Controller      |
| (Python Flask Webhook)    |
+-------------+-------------+
              |
      Attestation Check
  (Trusted Image Verification)
              |
    +---------+---------+
    |                   |
+---v---+           +---v---+
| Deny  |           | Allow |
| Pod   |           | Pod   |
+-------+           +-------+
```

## Features

- ✅ **Image Attestation**: Validates container images against a trusted images list
- ✅ **Multi-Container Support**: Handles pods with multiple containers and init containers
- ✅ **Security-First**: Uses SSL/TLS encryption for webhook communication
- ✅ **Minikube Ready**: Optimized for local development with Minikube
- ✅ **Comprehensive Testing**: Includes test pods for various scenarios
- ✅ **Easy Deployment**: Automated scripts for setup and teardown

## Quick Start

### Prerequisites

- Minikube installed and running
- kubectl configured to work with Minikube
- Docker installed
- OpenSSL installed

### 1. Start Minikube

```bash
minikube start
```

### 2. Deploy the Admission Controller

```bash
# Clone and navigate to the project
cd attestation-admission-controller

# Deploy everything (builds Docker image, generates certificates, deploys to Kubernetes)
./scripts/deploy.sh
```

### 3. Test the Admission Controller

```bash
# Run automated tests
./scripts/test.sh

# Or test manually:
# This should be ALLOWED (nginx:latest is trusted)
kubectl apply -f tests/trusted-pod.yaml

# This should be DENIED (redis:6.2 is not trusted)
kubectl apply -f tests/untrusted-pod.yaml
```

### 4. Monitor the Webhook

```bash
# View real-time logs
kubectl logs -l app=attestation-admission-controller -f

# Check webhook health
kubectl port-forward svc/attestation-admission-controller 8443:443
curl -k https://localhost:8443/health
```

### 5. Cleanup

```bash
./scripts/cleanup.sh
```

## Project Structure

```
attestation-admission-controller/
├── webhook.py                    # Main Flask application
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Container image definition
├── scripts/
│   ├── deploy.sh                # Main deployment script
│   ├── test.sh                  # Test script
│   ├── cleanup.sh               # Cleanup script
│   └── generate-certs.sh        # SSL certificate generation
├── k8s/
│   ├── deployment.yaml          # Kubernetes deployment
│   ├── service.yaml             # Kubernetes service
│   └── webhook-configuration.yaml # ValidatingAdmissionWebhook config
├── tests/
│   ├── trusted-pod.yaml         # Test pod with trusted image
│   ├── untrusted-pod.yaml       # Test pod with untrusted image
│   ├── mixed-pod.yaml           # Test pod with mixed images
│   └── all-trusted-pod.yaml     # Test pod with multiple trusted images
├── certs/                       # Generated certificates (created during deployment)
└── README.md                    # This file
```

## Configuration

### Trusted Images List

The trusted images are configured in `webhook.py`:

```python
TRUSTED_IMAGES = {
    "nginx:1.21",
    "nginx:latest", 
    "alpine:3.14",
    "alpine:latest",
    "python:3.9-slim",
    "busybox:latest",
    "hello-world:latest"
}
```

To modify the trusted images list:

1. Edit the `TRUSTED_IMAGES` set in `webhook.py`
2. Rebuild and redeploy:
   ```bash
   ./scripts/cleanup.sh
   ./scripts/deploy.sh
   ```

### Webhook Configuration

The webhook is configured to:
- Intercept pod creation requests (`CREATE` operations)
- Validate all containers and init containers
- Use `failurePolicy: Fail` (reject pods if webhook is unavailable)
- Exclude system namespaces (kube-system, kube-public, etc.)

## How It Works

1. **User submits a pod**: `kubectl apply -f pod.yaml`
2. **Kubernetes API Server**: Receives the request and checks for admission webhooks
3. **Admission Controller**: Receives an AdmissionReview request
4. **Image Validation**: Extracts all container images and checks against trusted list
5. **Response**: Returns AdmissionResponse with `allowed: true/false`
6. **Result**: Pod is either created or rejected based on the response

## Testing Scenarios

The project includes several test scenarios:

| Test File | Images | Expected Result |
|-----------|--------|-----------------|
| `trusted-pod.yaml` | nginx:latest | ✅ ALLOWED |
| `untrusted-pod.yaml` | redis:6.2 | ❌ DENIED |
| `mixed-pod.yaml` | nginx:latest + mysql:8.0 | ❌ DENIED |
| `all-trusted-pod.yaml` | busybox:latest + nginx:latest + alpine:latest | ✅ ALLOWED |

## Troubleshooting

### Common Issues

1. **Webhook not responding**:
   ```bash
   kubectl logs -l app=attestation-admission-controller
   kubectl get pods -l app=attestation-admission-controller
   ```

2. **Certificate issues**:
   ```bash
   kubectl get secret webhook-certs -o yaml
   ./scripts/generate-certs.sh  # Regenerate certificates
   ```

3. **Minikube Docker issues**:
   ```bash
   eval $(minikube docker-env)  # Switch to Minikube Docker
   docker images | grep attestation  # Check if image exists
   ```

4. **Webhook blocking everything**:
   ```bash
   # Emergency removal of webhook
   kubectl delete validatingadmissionwebhooks attestation-admission-controller
   ```

### Debug Mode

To enable debug logging in the webhook:

1. Edit `webhook.py` and change:
   ```python
   logging.basicConfig(level=logging.DEBUG)
   ```

2. Redeploy:
   ```bash
   ./scripts/cleanup.sh && ./scripts/deploy.sh
   ```

## Security Considerations

- **Certificate Management**: Uses self-signed certificates for simplicity. In production, use proper CA-signed certificates.
- **Image Verification**: This is a mock implementation. In production, integrate with actual attestation systems (like Sigstore, Notary, etc.).
- **Namespace Isolation**: Consider using different namespaces for the webhook and tested applications.
- **Resource Limits**: The webhook has resource limits to prevent resource exhaustion.

## Production Considerations

For production deployment:

1. **Use proper image attestation**: Replace the trusted images list with actual signature verification
2. **High Availability**: Deploy multiple replicas of the webhook
3. **Certificate Management**: Use cert-manager or similar for automatic certificate rotation
4. **Monitoring**: Add proper monitoring and alerting
5. **Security**: Run with minimal privileges and use admission controllers like OPA Gatekeeper

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly with `./scripts/test.sh`
5. Submit a pull request

## License

This project is provided as-is for educational purposes.
