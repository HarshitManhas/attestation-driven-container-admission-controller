# Complete Workflow Guide - Real Image Attestation Branch

This guide shows you **exactly what to do** to run the enhanced real attestation system and **what's different** from the original mock implementation.

## 🔄 What Stays the Same

The **basic deployment workflow** is identical to the original branch:

```bash
# Core workflow (unchanged)
./scripts/cleanup.sh    # Clean existing resources
./scripts/deploy.sh     # Build image & deploy system  
./scripts/test.sh       # Test the system
```

## 🆕 What's New & Enhanced

### New Files Added:
- `image_attestation.py` - Real Cosign/Sigstore integration
- `policy_config.py` - Flexible policy management system
- `tools/sign-image.sh` - Complete image signing toolkit
- `config/sample-policy.yaml` - Policy configuration examples
- `k8s/configmap.yaml` - Policy and configuration management
- `README-REAL-ATTESTATION.md` - Comprehensive documentation

### Enhanced Files:
- `webhook.py` - Now uses real attestation instead of mock trusted images
- `requirements.txt` - Added cryptography and other attestation libraries
- `Dockerfile` - Now includes Cosign binary installation
- `k8s/deployment.yaml` - Enhanced with attestation configuration

## 📋 Complete Step-by-Step Workflow

### Prerequisites (Same as Before)
```bash
# Ensure Minikube is running
minikube status
# If stopped, start it:
minikube start

# Verify kubectl access
kubectl get nodes
```

### Step 1: Deploy the Real Attestation System
```bash
# Clean up any existing deployment
./scripts/cleanup.sh

# Deploy the enhanced system (builds image with Cosign + deploys)
./scripts/deploy.sh

# Deploy the policy configuration (NEW STEP)
kubectl apply -f k8s/configmap.yaml
```

### Step 2: Verify Deployment
```bash
# Check if webhook is running
kubectl get pods -l app=attestation-admission-controller

# Check logs (should show "Real Image Attestation" startup)
kubectl logs -l app=attestation-admission-controller

# Expected log output:
# INFO:__main__:Starting Real Image Attestation Admission Controller
# INFO:__main__:Policy configuration loaded: {...}
```

### Step 3: Test Basic Functionality
```bash
# Test with the original test suite (still works!)
./scripts/test.sh

# Or test individual scenarios
kubectl apply -f tests/trusted-pod.yaml      # Should succeed
kubectl apply -f tests/untrusted-pod.yaml    # Should succeed (policy allows unsigned images initially)
```

### Step 4: Explore New Features

#### A) Check Policy Configuration
```bash
# Port forward to access new API endpoints
kubectl port-forward svc/attestation-admission-controller 8443:443 &

# View current policy
curl -k https://localhost:8443/policy-summary

# Test manual verification
curl -k -X POST https://localhost:8443/verify-image \
  -H "Content-Type: application/json" \
  -d '{"image": "nginx:latest", "namespace": "default"}'
```

#### B) Try Image Signing (Optional)
```bash
# Install Cosign locally (if you want to sign images)
# Ubuntu/Debian:
wget "https://github.com/sigstore/cosign/releases/download/v2.2.4/cosign-linux-amd64"
sudo mv cosign-linux-amd64 /usr/local/bin/cosign
sudo chmod +x /usr/local/bin/cosign

# Use our signing tool
./tools/sign-image.sh generate-keys   # Generate key pair
./tools/sign-image.sh --help          # See all options
```

## 🔍 Key Differences from Original Branch

### 1. **Verification Logic Changed**
**Before (Mock):**
```python
# Old: Simple string matching against TRUSTED_IMAGES set
TRUSTED_IMAGES = {"nginx:latest", "alpine:latest", ...}
return image_name in TRUSTED_IMAGES
```

**Now (Real Attestation):**
```python
# New: Real Cosign signature verification
result = self.attestation_verifier.verify_image_attestation(image)
# Checks actual signatures using Cosign CLI
```

### 2. **Policy System**
**Before:** Hard-coded trusted images list
**Now:** Flexible YAML-based policies:
```yaml
# Can configure per-namespace
namespaces:
  - namespace: "production"
    require_signature: true
    
# Can configure per-image pattern  
images:
  - image_pattern: "nginx:*"
    require_signature: true
```

### 3. **New API Endpoints**
**Added endpoints:**
- `GET /policy-summary` - View policy configuration
- `POST /policy-reload` - Reload policy from ConfigMap
- `POST /clear-cache` - Clear verification cache
- `POST /verify-image` - Manual image verification

### 4. **Environment Configuration**
**New environment variables:**
```bash
ATTESTATION_REQUIRE_SIGNATURE=true/false
POLICY_CONFIG_PATH=/etc/attestation/policy.yaml
ATTESTATION_PUBLIC_KEYS=/etc/attestation/cosign.pub
ATTESTATION_EMERGENCY_BYPASS=false
```

## 🧪 Testing Scenarios

### Basic Testing (Same as Before)
```bash
./scripts/test.sh
# Tests still work - all should pass since policy allows unsigned images initially
```

### Advanced Testing (New)
```bash
# Test policy changes
kubectl edit configmap attestation-config
# Change require_signature to true, save

# Reload policy
curl -k -X POST https://localhost:8443/policy-reload

# Now test with unsigned image - should be rejected
kubectl run test-strict --image=redis:latest
```

## 🔧 Configuration Options

### Current Default Policy (Permissive for Testing)
```yaml
global:
  default_require_signature: false  # Allows unsigned images
  exempt_namespaces:
    - "kube-system"
    - "kube-public" 
    - "kube-node-lease"
```

### Production-Ready Policy Example
```yaml
global:
  default_require_signature: true   # Require signatures
  allowed_signers:
    - "security@company.com"
namespaces:
  - namespace: "development"
    require_signature: false        # Dev can use unsigned
```

## 🚨 Emergency Procedures

### If Webhook Blocks Everything
```bash
# Emergency webhook removal (same as before)
kubectl delete validatingwebhookconfigurations attestation-admission-controller

# Or enable emergency bypass
kubectl patch configmap attestation-config --patch '{"data":{"policy.yaml":"emergency_bypass: true\n"}}'
curl -k -X POST https://localhost:8443/policy-reload
```

## 📊 What You Get Now vs Before

| Feature | Original Branch | Real Attestation Branch |
|---------|----------------|-------------------------|
| Image Verification | Mock (string matching) | **Real Cosign signatures** |
| Policy System | Hard-coded list | **Flexible YAML policies** |
| Performance | Fast (in-memory) | **Cached (5-min TTL)** |
| Management | Basic | **Full API endpoints** |
| Security | Basic admission control | **Enterprise-grade attestation** |
| Signing Tools | None | **Complete toolkit** |
| Emergency Bypass | Manual kubectl | **Policy-based + API** |
| Documentation | Basic | **Comprehensive** |

## 🎯 Summary

**You still use the same basic workflow:**
```bash
./scripts/deploy.sh    # Just run this!
./scripts/test.sh      # Test it!
```

**But now you also get:**
- Real signature verification (when enabled)
- Flexible policy management
- Professional API endpoints  
- Complete signing toolkit
- Enterprise security features

The system is **backward compatible** - all your existing tests and workflows work, but now you have the option to enable real attestation when ready!

## 🔄 Migration Path

1. **Week 1**: Deploy and test with current permissive policy ✅ (You're here!)
2. **Week 2**: Start signing critical images with `./tools/sign-image.sh`
3. **Week 3**: Enable signature requirements for production namespace
4. **Week 4**: Roll out signature requirements cluster-wide

The beauty is you can make this transition **gradually** without breaking existing workloads!
