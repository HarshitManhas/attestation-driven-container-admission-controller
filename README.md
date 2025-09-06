# Attestation-Driven Container Admission Controller

A Kubernetes ValidatingAdmissionWebhook that implements container image attestation to ensure only trusted images can be deployed in your cluster.

## 🌟 Branch Overview

This project has evolved into two distinct implementations:

### 🎯 **Current Branch: `feature/real-image-attestation`** (You are here!)
- **✅ REAL Cosign/Sigstore Integration**: Actual container image signature verification
- **✅ Enterprise-Ready**: Production-grade attestation with policy management
- **✅ Flexible Policies**: YAML-based configuration with namespace/image-specific rules
- **✅ Complete Toolkit**: Image signing tools and comprehensive API endpoints
- **✅ Backward Compatible**: All original workflows still work + new capabilities

### 📚 **Original Branch: `main`** 
- **📝 Mock Implementation**: Simple trusted images list (educational/demo purposes)
- **🎓 Learning-Focused**: Easy to understand admission webhook concepts
- **⚡ Fast Setup**: Minimal dependencies, quick to deploy and test
- **🔧 Foundation**: Solid base that this enhanced branch builds upon

### 🤔 **Which Branch Should You Use?**

| Use Case | Recommended Branch |
|----------|-------------------|
| **Production deployment** | `feature/real-image-attestation` |
| **Learning admission webhooks** | `main` (simpler to understand) |
| **Enterprise security** | `feature/real-image-attestation` |
| **Quick demo/proof-of-concept** | `main` (faster setup) |
| **Real image signing workflow** | `feature/real-image-attestation` |

---

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

### 🚀 **Real Attestation Branch Features** (Current)

- ✅ **REAL Cosign Signature Verification**: Actual cryptographic verification using Sigstore/Cosign
- ✅ **Flexible Policy System**: YAML-based policies with namespace and image-specific rules
- ✅ **Enterprise Security**: Emergency bypass, transparency log integration, certificate chains
- ✅ **Performance Optimized**: Caching system with TTL to avoid repeated verification
- ✅ **Complete API Management**: Policy reload, cache clearing, manual verification endpoints
- ✅ **Image Signing Toolkit**: Full toolset for signing container images with Cosign
- ✅ **Multi-Container Support**: Handles pods with multiple containers and init containers
- ✅ **Security-First**: Uses SSL/TLS encryption for webhook communication
- ✅ **Production Ready**: Comprehensive logging, metrics, and enterprise features
- ✅ **Backward Compatible**: All original workflows work + massive new capabilities

### 📋 **Original Branch Features** (`main` branch)

- ✅ **Simple Image Validation**: Mock trusted images list (educational)
- ✅ **Multi-Container Support**: Handles pods with multiple containers and init containers  
- ✅ **Security-First**: Uses SSL/TLS encryption for webhook communication
- ✅ **Minikube Ready**: Optimized for local development with Minikube
- ✅ **Comprehensive Testing**: Includes test pods for various scenarios
- ✅ **Easy Deployment**: Automated scripts for setup and teardown


### 🔄 **Migration Path**

If you're coming from the original branch:

```bash
# Switch to the enhanced branch
git checkout feature/real-image-attestation

# Everything still works the same way!
./scripts/deploy.sh
./scripts/test.sh

# Plus you get all the new features
kubectl apply -f k8s/configmap.yaml  # New: Policy management
./tools/sign-image.sh --help          # New: Image signing tools
```

## Quick Start

> 📝 **Note**: This is the **Real Attestation Branch** with enterprise-grade features. For the simpler educational version, switch to the `main` branch.

### Prerequisites

- Minikube installed and running
- kubectl configured to work with Minikube
- Docker installed
- OpenSSL installed
- **New**: Cosign binary (installed automatically in container)

### 1. Start Minikube

```bash
minikube start
```

### 2. Deploy the Real Attestation System

```bash
# Clone and navigate to the project
cd attestation-admission-controller

# Deploy everything (builds Docker image with Cosign, generates certificates, deploys to Kubernetes)
./scripts/deploy.sh

# Deploy policy configuration (NEW STEP for real attestation)
kubectl apply -f k8s/configmap.yaml
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

### 4. Monitor the Real Attestation System

```bash
# View real-time logs (now shows attestation verification details)
kubectl logs -l app=attestation-admission-controller -f

# Check webhook health and new endpoints
kubectl port-forward svc/attestation-admission-controller 8443:443 &
curl -k https://localhost:8443/health

# NEW: Check policy configuration
curl -k https://localhost:8443/policy-summary

# NEW: Manually test image verification
curl -k -X POST https://localhost:8443/verify-image \
  -H "Content-Type: application/json" \
  -d '{"image": "nginx:latest", "namespace": "default"}'
```

### 5. Cleanup

```bash
./scripts/cleanup.sh
```

## Project Structure

### 🎆 **Real Attestation Branch Structure** (Current)

```
attestation-admission-controller/
├── webhook.py                    # Main Flask application (ENHANCED)
├── image_attestation.py          # NEW: Real Cosign verification engine
├── policy_config.py              # NEW: Flexible policy management system
├── requirements.txt              # Python dependencies (ENHANCED)
├── Dockerfile                    # Container image definition (+ Cosign binary)
├── scripts/
│   ├── deploy.sh                # Main deployment script
│   ├── test.sh                  # Test script
│   ├── cleanup.sh               # Cleanup script
│   └── generate-certs.sh        # SSL certificate generation
├── tools/                       # NEW: Image signing toolkit
│   └── sign-image.sh            # Complete Cosign signing tool
├── config/                      # NEW: Configuration examples
│   └── sample-policy.yaml       # Policy configuration examples
├── k8s/
│   ├── deployment.yaml          # Kubernetes deployment (ENHANCED)
│   ├── service.yaml             # Kubernetes service
│   ├── configmap.yaml           # NEW: Policy and configuration management
│   └── webhook-configuration.yaml # ValidatingAdmissionWebhook config
├── tests/
│   ├── trusted-pod.yaml         # Test pod with trusted image
│   ├── untrusted-pod.yaml       # Test pod with untrusted image
│   ├── mixed-pod.yaml           # Test pod with mixed images
│   └── all-trusted-pod.yaml     # Test pod with multiple trusted images
├── certs/                       # Generated certificates (created during deployment)
├── README.md                    # This file (ENHANCED with branch comparison)
├── README-REAL-ATTESTATION.md   # NEW: Comprehensive real attestation guide
└── COMPLETE-WORKFLOW.md         # NEW: Complete workflow and migration guide
```

## Configuration

### 🎆 **Real Attestation Policy System** (Current Branch)

The system now uses **flexible YAML-based policies** instead of hard-coded lists:

```yaml
# Example policy configuration
version: "1.0"
global:
  default_require_signature: false  # Start permissive for testing
  require_transparency_log: true
  exempt_namespaces:
    - "kube-system"
    - "development"
  
namespaces:
  - namespace: "production"
    require_signature: true
    allowed_signers:
      - "production@company.com"
    min_slsa_level: 3

images:
  - image_pattern: "nginx:*"
    require_signature: true
    allowed_signers:
      - "nginx-maintainer@nginx.org"
```

**To modify policies:**

```bash
# Method 1: Edit ConfigMap directly
kubectl edit configmap attestation-config

# Method 2: Update and apply
cp config/sample-policy.yaml my-policy.yaml
# Edit my-policy.yaml
kubectl create configmap attestation-config --from-file=policy.yaml=my-policy.yaml --dry-run=client -o yaml | kubectl apply -f -

# Method 3: Live reload (no restart needed!)
curl -k -X POST https://localhost:8443/policy-reload
```

### 📋 **Original Branch Configuration** (`main` branch)

For comparison, the original branch uses a simple hard-coded list:

```python
# Original method (main branch only)
TRUSTED_IMAGES = {"nginx:latest", "alpine:latest", ...}
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

### 🎆 **Real Attestation Branch** (Current - Production Ready)

- **✅ Real Cryptographic Verification**: Uses actual Cosign/Sigstore signature verification
- **✅ Certificate Management**: Advanced certificate chain validation + transparency logs
- **✅ Policy Security**: RBAC-controlled policy management with live reload
- **✅ Emergency Bypass**: Secure token-based bypass with audit logging
- **✅ Performance Security**: TTL-based caching prevents DoS while maintaining security
- **✅ Transparency Logs**: Rekor integration for tamper-evident signature verification
- **✅ SLSA Provenance**: Full supply chain attestation support

### 📋 **Original Branch** (`main` - Demo/Learning)

- **Certificate Management**: Uses self-signed certificates for simplicity
- **Image Verification**: Mock implementation for educational purposes
- **Namespace Isolation**: Consider using different namespaces for webhook and applications
- **Resource Limits**: Basic resource limits to prevent exhaustion

## Production Considerations

### 🎆 **Real Attestation Branch** (Ready for Production)

**✅ Already Production-Ready Features:**
1. **Real Image Attestation**: ✅ Uses industry-standard Cosign/Sigstore
2. **Enterprise Security**: ✅ Policy management, emergency bypass, audit logs
3. **High Availability**: ✅ Stateless design with caching for performance
4. **Monitoring**: ✅ Comprehensive API endpoints and metrics
5. **Certificate Management**: ✅ Advanced cert handling (can integrate with cert-manager)

**Additional Production Enhancements:**
- Deploy multiple replicas for HA
- Integrate with enterprise OIDC providers for keyless signing
- Set up monitoring dashboards for attestation metrics
- Configure backup policies and disaster recovery

### 📋 **Original Branch** (Educational/Demo)

**Requires Major Changes for Production:**
1. **❌ Replace mock verification**: Integrate with actual attestation systems
2. **❌ Add policy management**: Build configuration system
3. **❌ Add monitoring**: Implement metrics and alerting
4. **❌ Add security features**: Emergency bypass, audit logging
5. **❌ Performance optimization**: Add caching and optimization

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly with `./scripts/test.sh`
5. Submit a pull request

## 📚 Quick Reference

### 👍 **For New Users**
- **Want to learn?** → Switch to `main` branch (simpler mock implementation)
- **Want production security?** → Stay on `feature/real-image-attestation` (current)
- **Quick deploy**: `./scripts/deploy.sh && kubectl apply -f k8s/configmap.yaml`

### 🚀 **Key Commands (Real Attestation Branch)**

```bash
# Deploy everything
./scripts/deploy.sh
kubectl apply -f k8s/configmap.yaml

# Test the system
./scripts/test.sh

# Monitor and manage
kubectl port-forward svc/attestation-admission-controller 8443:443 &
curl -k https://localhost:8443/policy-summary
curl -k -X POST https://localhost:8443/policy-reload

# Sign images (optional)
./tools/sign-image.sh generate-keys
./tools/sign-image.sh sign nginx:latest

# Emergency procedures
kubectl delete validatingwebhookconfigurations attestation-admission-controller
```

### 📄 **Documentation**
- **This file**: Overview and branch comparison
- **`README-REAL-ATTESTATION.md`**: Comprehensive real attestation guide
- **`COMPLETE-WORKFLOW.md`**: Complete workflow and migration guide
- **`config/sample-policy.yaml`**: Policy configuration examples

### 🎆 **What Makes This Branch Special**
✅ **Real Cosign Integration** • ✅ **Flexible Policies** • ✅ **Enterprise Features**  
✅ **Production Ready** • ✅ **Backward Compatible** • ✅ **Complete Toolkit**

---

## License

This project is provided as-is for educational purposes.
