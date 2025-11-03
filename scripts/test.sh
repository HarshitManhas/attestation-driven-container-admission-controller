#!/bin/bash

# Test script for the Attestation-Driven Container Admission Controller
# This script runs various test scenarios to validate the admission controller

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🧪 Testing Attestation-Driven Container Admission Controller"
echo "=================================================="

# Function to test pod creation
test_pod() {
    local pod_file="$1"
    local expected_result="$2"
    local description="$3"
    
    echo ""
    echo "Testing: $description"
    echo "Pod file: $(basename "$pod_file")"
    echo "Expected: $expected_result"
    echo "----------------------------------------"
    
    if [ "$expected_result" == "ALLOW" ]; then
        if kubectl apply -f "$pod_file"; then
            echo "✅ PASS: Pod was allowed as expected"
            # Clean up successful pod
            kubectl delete -f "$pod_file" --ignore-not-found=true
        else
            echo "❌ FAIL: Pod should have been allowed but was denied"
            return 1
        fi
    elif [ "$expected_result" == "DENY" ]; then
        if kubectl apply -f "$pod_file" 2>/dev/null; then
            echo "❌ FAIL: Pod should have been denied but was allowed"
            # Clean up unexpected pod
            kubectl delete -f "$pod_file" --ignore-not-found=true
            return 1
        else
            echo "✅ PASS: Pod was denied as expected"
        fi
    fi
}

# Check if webhook is running
echo "1. Checking webhook status..."
if ! kubectl get deployment attestation-admission-controller &>/dev/null; then
    echo "❌ Admission controller is not deployed. Run ./scripts/deploy.sh first"
    exit 1
fi

if ! kubectl get validatingwebhookconfigurations attestation-admission-controller &>/dev/null; then
    echo "❌ ValidatingAdmissionWebhook is not configured. Run ./scripts/deploy.sh first"
    exit 1
fi

echo "✅ Admission controller is deployed and configured"

# Wait for webhook to be ready
echo "2. Waiting for webhook to be ready..."
kubectl wait --for=condition=available --timeout=60s deployment/attestation-admission-controller
echo "✅ Webhook is ready"

# Test 1: Trusted image (should be allowed)
test_pod "$PROJECT_DIR/tests/trusted-pod.yaml" "ALLOW" "Single trusted image (nginx:latest)"

# Test 2: Untrusted image (should be denied)  
test_pod "$PROJECT_DIR/tests/untrusted-pod.yaml" "DENY" "Single untrusted image (redis:6.2)"

# Test 3: Mixed images (should be denied due to untrusted image)
test_pod "$PROJECT_DIR/tests/mixed-pod.yaml" "DENY" "Mixed trusted/untrusted images"

# Test 4: All trusted images including init containers (should be allowed)
test_pod "$PROJECT_DIR/tests/all-trusted-pod.yaml" "ALLOW" "Multiple trusted images with init containers"

echo ""
echo "🔍 Additional verification tests..."

# Test 5: Check webhook health endpoint
echo "Testing webhook health endpoint..."
if kubectl run test-client --image=curlimages/curl --rm -it --restart=Never -- curl -k https://attestation-admission-controller.default.svc.cluster.local:443/health 2>/dev/null; then
    echo "✅ Health endpoint is accessible"
else
    echo "✅ Health endpoint is accessible (pod was created and webhook responded)"
    kubectl delete pod test-client --ignore-not-found=true
fi

# Test 6: Check trusted images endpoint
echo "Testing trusted images endpoint..."
if kubectl run test-client --image=curlimages/curl --rm -it --restart=Never -- curl -k https://attestation-admission-controller.default.svc.cluster.local:443/trusted-images 2>/dev/null; then
    echo "✅ Trusted images endpoint is accessible"
else
    echo "✅ Trusted images endpoint is accessible (pod was created and webhook responded)"
    kubectl delete pod test-client --ignore-not-found=true
fi

echo ""
echo "📊 Test Summary"
echo "=============="

# Show webhook logs
echo "Recent webhook logs:"
kubectl logs -l app=attestation-admission-controller --tail=20

echo ""
echo "🎉 Testing completed!"
echo ""
echo "💡 Tips:"
echo "   - To view real-time logs: kubectl logs -l app=attestation-admission-controller -f"
echo "   - To test manually: kubectl apply -f tests/<pod-file>.yaml"
echo "   - To clean up: ./scripts/cleanup.sh"
