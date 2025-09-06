# Real Image Attestation & Signing Implementation

This document describes the real image attestation and signing implementation for the Kubernetes admission controller.

## Overview

The admission controller has been enhanced with **real image attestation verification** using industry-standard tools and protocols:

- **Sigstore/Cosign** for container image signing and verification
- **Flexible policy system** for defining attestation requirements per namespace/image
- **Multiple signature formats** support (Cosign, Notary v2 ready)
- **Transparency log integration** (Rekor)
- **SLSA provenance** support
- **Caching system** for performance
- **Emergency bypass** capabilities

## Architecture

### Components

1. **ImageAttestationVerifier** (`image_attestation.py`)
   - Core verification engine using Cosign CLI and Sigstore libraries
   - Supports keyless and key-based verification
   - Caching for performance
   - Multiple signature format support

2. **PolicyManager** (`policy_config.py`)
   - Flexible policy configuration system
   - Namespace and image-specific rules
   - Environment variable and YAML configuration support
   - Priority-based policy resolution

3. **RealAdmissionController** (`webhook.py`)
   - Updated admission controller with real attestation
   - Integration with policy and verification systems
   - Enhanced logging and metrics
   - Emergency bypass support

4. **Signing Tools** (`tools/sign-image.sh`)
   - Command-line tool for signing container images
   - Supports key-based and keyless signing
   - SLSA attestation support
   - Verification capabilities

## Quick Start

### 1. Install Dependencies

Install Cosign (required for signature verification):
```bash
# Install Cosign
go install github.com/sigstore/cosign/v2/cmd/cosign@latest

# Or using package manager (Ubuntu/Debian)
wget "https://github.com/sigstore/cosign/releases/download/v2.2.4/cosign-linux-amd64"
sudo mv cosign-linux-amd64 /usr/local/bin/cosign
sudo chmod +x /usr/local/bin/cosign
```

### 2. Deploy with Real Attestation

Deploy the enhanced admission controller:
```bash
# Build and deploy
./scripts/cleanup.sh
./scripts/deploy.sh

# Deploy policy configuration
kubectl apply -f k8s/configmap.yaml
```

### 3. Configure Policies

Edit the policy configuration:
```bash
# Edit the ConfigMap directly
kubectl edit configmap attestation-config

# Or create your own policy file
cp config/sample-policy.yaml my-policy.yaml
# Edit my-policy.yaml as needed
kubectl create configmap attestation-config --from-file=policy.yaml=my-policy.yaml --dry-run=client -o yaml | kubectl apply -f -
```

### 4. Sign Test Images

Generate signing keys and sign images:
```bash
# Generate Cosign key pair
./tools/sign-image.sh generate-keys

# Sign an image
docker pull nginx:latest
docker tag nginx:latest my-registry.io/nginx:latest
docker push my-registry.io/nginx:latest
./tools/sign-image.sh sign my-registry.io/nginx:latest

# Or use keyless signing (requires OIDC authentication)
./tools/sign-image.sh keyless-sign my-registry.io/nginx:latest
```

### 5. Test the System

Test with signed and unsigned images:
```bash
# Test with a signed image (should succeed if policy allows)
kubectl run test-signed --image=my-registry.io/nginx:latest

# Test with an unsigned image (should fail if policy requires signatures)
kubectl run test-unsigned --image=nginx:latest

# Check admission controller logs
kubectl logs -l app=attestation-admission-controller -f
```

## Policy Configuration

### Policy Structure

Policies are defined in YAML with three levels of configuration:

1. **Global Policy** - Default settings for all images
2. **Namespace Policies** - Override global settings for specific namespaces
3. **Image Policies** - Override settings for specific image patterns (highest priority)

### Example Policy

```yaml
version: "1.0"
global:
  default_require_signature: true
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
    require_provenance: true

images:
  - image_pattern: "nginx:*"
    require_signature: true
    allowed_signers:
      - "nginx-maintainer@nginx.org"
    priority: 100
```

### Policy Settings

- `require_signature`: Whether image signatures are required
- `allowed_signers`: List of allowed signer emails or key fingerprints
- `allowed_registries`: List of allowed container registries
- `require_transparency_log`: Require Rekor transparency log entries
- `require_certificate_chain`: Require certificate chain validation
- `min_slsa_level`: Minimum SLSA provenance level
- `require_provenance`: Require SLSA provenance attestations
- `exempt_namespaces`: Namespaces exempt from attestation
- `exempt_images`: Image patterns exempt from attestation
- `emergency_bypass`: Enable emergency bypass functionality

## Environment Variables

Key environment variables for configuration:

### Attestation Settings
```bash
ATTESTATION_REQUIRE_SIGNATURE=true
ATTESTATION_REQUIRE_TRANSPARENCY_LOG=true
ATTESTATION_ALLOWED_SIGNERS="signer1@company.com,signer2@company.com"
ATTESTATION_EXEMPT_NAMESPACES="kube-system,development"
ATTESTATION_EMERGENCY_BYPASS=false
ATTESTATION_EMERGENCY_BYPASS_TOKEN="secure-token"
```

### File Paths
```bash
POLICY_CONFIG_PATH="/etc/attestation/policy.yaml"
ATTESTATION_PUBLIC_KEYS="/etc/attestation/cosign.pub"
```

### Cosign/Sigstore Settings
```bash
COSIGN_EXPERIMENTAL=1  # Enable keyless verification
SIGSTORE_CT_LOG_PUBLIC_KEY_FILE="/etc/ssl/certs/fulcio-root.crt.pem"
SIGSTORE_REKOR_PUBLIC_KEY="/etc/ssl/certs/rekor.pub"
```

## API Endpoints

The admission controller exposes several new endpoints:

### Management Endpoints
- `GET /health` - Health check
- `GET /policy-summary` - Current policy configuration summary
- `POST /policy-reload` - Reload policy from configuration file
- `POST /clear-cache` - Clear attestation verification cache

### Testing Endpoints
- `POST /verify-image` - Manually verify image attestation
  ```bash
  curl -k -X POST https://localhost:8443/verify-image \
    -H "Content-Type: application/json" \
    -d '{"image": "nginx:latest", "namespace": "default"}'
  ```

### Access Endpoints
```bash
# Port forward to access endpoints
kubectl port-forward svc/attestation-admission-controller 8443:443

# Check policy summary
curl -k https://localhost:8443/policy-summary

# Reload policy
curl -k -X POST https://localhost:8443/policy-reload

# Test image verification
curl -k -X POST https://localhost:8443/verify-image \
  -H "Content-Type: application/json" \
  -d '{"image": "nginx:latest", "namespace": "default"}'
```

## Signature Verification Process

1. **Policy Resolution**
   - Determine applicable policy for namespace and image
   - Check exemptions and emergency bypass

2. **Cosign Verification**
   - Attempt keyless verification first (if configured)
   - Fall back to key-based verification
   - Validate transparency log entries
   - Check certificate chains

3. **Policy Enforcement**
   - Validate signers against allowed list
   - Check registry restrictions
   - Verify SLSA requirements
   - Apply custom policy rules

4. **Caching**
   - Cache verification results (5-minute TTL by default)
   - Avoid repeated verification of same images

## Image Signing Workflow

### Key-Based Signing

1. **Generate Keys**
   ```bash
   ./tools/sign-image.sh generate-keys
   ```

2. **Sign Images**
   ```bash
   ./tools/sign-image.sh sign my-app:v1.0.0
   ```

3. **Configure Public Key**
   ```bash
   kubectl create configmap cosign-config --from-file=cosign.pub
   ```

### Keyless Signing (Recommended for Production)

1. **Sign with OIDC**
   ```bash
   ./tools/sign-image.sh keyless-sign my-app:v1.0.0
   ```

2. **Configure Verification**
   - Set allowed OIDC issuers in policy
   - Configure certificate identity patterns

### SLSA Attestations

1. **Create Provenance**
   ```json
   {
     "buildType": "https://slsa.dev/build-type",
     "builder": {"id": "https://github.com/actions"},
     "materials": [{"uri": "git+https://github.com/org/repo@abc123"}]
   }
   ```

2. **Sign with Attestation**
   ```bash
   ./tools/sign-image.sh sign-with-attestation my-app:v1.0.0 provenance.json
   ```

## Troubleshooting

### Common Issues

1. **Cosign Not Found**
   ```
   Error: cosign not found in PATH
   ```
   Solution: Install Cosign following the installation instructions

2. **Image Not Signed**
   ```
   Pod rejected: No valid signatures found
   ```
   Solution: Sign the image or update policy to allow unsigned images

3. **Policy Violation**
   ```
   Pod rejected: Policy violation - Signer not in allowed signers list
   ```
   Solution: Update policy to include the signer or re-sign with allowed signer

4. **Verification Timeout**
   ```
   Cosign verification timed out
   ```
   Solution: Check network connectivity to registries and transparency log

### Debug Commands

```bash
# Check admission controller logs
kubectl logs -l app=attestation-admission-controller -f

# Test Cosign verification manually
cosign verify --key cosign.pub nginx:latest

# Check policy configuration
kubectl get configmap attestation-config -o yaml

# Test webhook connectivity
kubectl port-forward svc/attestation-admission-controller 8443:443
curl -k https://localhost:8443/health
```

### Performance Tuning

1. **Increase Cache TTL**
   ```yaml
   env:
   - name: ATTESTATION_CACHE_TTL
     value: "600"  # 10 minutes
   ```

2. **Adjust Resource Limits**
   ```yaml
   resources:
     limits:
       memory: 512Mi
       cpu: 300m
   ```

3. **Configure Timeout**
   ```yaml
   env:
   - name: ATTESTATION_VERIFICATION_TIMEOUT
     value: "30"  # 30 seconds
   ```

## Security Considerations

1. **Private Key Management**
   - Store private keys securely (Kubernetes Secrets, HSM, KMS)
   - Rotate keys regularly
   - Use keyless signing for production when possible

2. **Policy Security**
   - Restrict access to policy ConfigMaps
   - Use RBAC to control policy modifications
   - Audit policy changes

3. **Emergency Bypass**
   - Use strong, random bypass tokens
   - Rotate tokens regularly
   - Monitor bypass usage
   - Disable when not needed

4. **Network Security**
   - Ensure secure connectivity to transparency logs
   - Use private registries when possible
   - Implement network policies

## Migration from Mock Implementation

To migrate from the mock trusted images implementation:

1. **Update Policies**
   - Convert `TRUSTED_IMAGES` list to policy configuration
   - Define appropriate namespace and image policies

2. **Sign Existing Images**
   - Identify currently trusted images
   - Sign with appropriate keys/certificates
   - Update registry with signed versions

3. **Gradual Rollout**
   - Start with `require_signature: false` in policies
   - Enable signature requirements incrementally
   - Monitor logs for verification issues

4. **Test Thoroughly**
   - Test with both signed and unsigned images
   - Verify policy enforcement works correctly
   - Test emergency bypass functionality

This real attestation implementation provides enterprise-grade container image security while maintaining flexibility and ease of use.
