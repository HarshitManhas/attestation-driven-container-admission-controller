#!/usr/bin/env python3
"""
Attestation-Driven Container Admission Controller
A Kubernetes ValidatingAdmissionWebhook that verifies container image attestations
"""

import json
import base64
import logging
import time
from flask import Flask, request, jsonify
from typing import Dict, List, Any
from image_attestation import ImageAttestationVerifier, AttestationStatus, create_default_policy
from policy_config import PolicyManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class RealAdmissionController:
    """Real admission controller with image attestation verification"""
    
    def __init__(self):
        """Initialize the admission controller with real attestation verification"""
        self.policy_manager = PolicyManager()
        # Create a default verifier - policies will be applied per-request
        default_policy = create_default_policy()
        self.attestation_verifier = ImageAttestationVerifier(default_policy)
        logger.info("Real attestation admission controller initialized")
    
    def verify_image_attestation(self, image: str, namespace: str) -> tuple[bool, str]:
        """
        Verify image attestation based on policy
        
        Args:
            image: Container image reference
            namespace: Kubernetes namespace
            
        Returns:
            Tuple of (is_allowed, message)
        """
        try:
            # Get policy for this specific namespace/image combination
            policy = self.policy_manager.get_policy_for_request(namespace, image)
            
            # If policy doesn't require signature, allow the image
            if not policy.require_signature:
                return True, f"Image {image} allowed (signature not required for namespace {namespace})"
            
            # Update verifier policy and verify attestation
            self.attestation_verifier.policy = policy
            result = self.attestation_verifier.verify_image_attestation(image)
            
            if result.status == AttestationStatus.VERIFIED:
                message = f"Image {image} verified: {result.message}"
                if result.signer:
                    message += f" (signed by: {result.signer})"
                return True, message
            
            elif result.status == AttestationStatus.NOT_SIGNED:
                return False, f"Image {image} rejected: No valid signatures found"
            
            elif result.status == AttestationStatus.FAILED:
                return False, f"Image {image} rejected: Signature verification failed - {result.message}"
            
            elif result.status == AttestationStatus.POLICY_VIOLATION:
                return False, f"Image {image} rejected: Policy violation - {result.message}"
            
            else:  # ERROR status
                return False, f"Image {image} rejected: Verification error - {result.message}"
                
        except Exception as e:
            logger.error(f"Error verifying attestation for {image}: {e}")
            return False, f"Image {image} rejected: Internal verification error"
    
    def extract_images_from_pod(self, pod_spec: Dict[Any, Any]) -> List[str]:
        """Extract all container images from a pod specification"""
        images = []
        
        # Check main containers
        containers = pod_spec.get("spec", {}).get("containers", [])
        for container in containers:
            if "image" in container:
                images.append(container["image"])
        
        # Check init containers
        init_containers = pod_spec.get("spec", {}).get("initContainers", [])
        for container in init_containers:
            if "image" in container:
                images.append(container["image"])
        
        return images
    
    def create_admission_response(self, allowed: bool, message: str = "", uid: str = "") -> Dict[str, Any]:
        """Create a standardized admission response"""
        return {
            "apiVersion": "admission.k8s.io/v1",
            "kind": "AdmissionReview",
            "response": {
                "uid": uid,
                "allowed": allowed,
                "status": {
                    "message": message
                }
            }
        }
    
    def validate_pod(self, admission_review: Dict[str, Any]) -> Dict[str, Any]:
        """Main validation logic for pods using real attestation"""
        try:
            # Extract the pod object from the admission request
            request_info = admission_review.get("request", {})
            pod = request_info.get("object", {})
            uid = request_info.get("uid", "")
            namespace = request_info.get("namespace", "default")
            
            pod_name = pod.get('metadata', {}).get('name', 'unknown')
            logger.info(f"Validating pod: {pod_name} in namespace: {namespace}")
            
            # Check for emergency bypass
            bypass_token = request_info.get("userInfo", {}).get("extra", {}).get("bypass-token")
            if self.policy_manager.is_emergency_bypass_enabled(bypass_token):
                logger.warning(f"Emergency bypass activated for pod {pod_name}")
                return self.create_admission_response(
                    allowed=True,
                    message="Pod allowed via emergency bypass",
                    uid=uid
                )
            
            # Extract all images from the pod
            images = self.extract_images_from_pod(pod)
            
            if not images:
                return self.create_admission_response(
                    allowed=True, 
                    message="No images found in pod specification", 
                    uid=uid
                )
            
            # Verify attestation for each image
            failed_images = []
            verification_messages = []
            
            start_time = time.time()
            
            for image in images:
                is_allowed, message = self.verify_image_attestation(image, namespace)
                verification_messages.append(f"  {image}: {message}")
                
                if not is_allowed:
                    failed_images.append(image)
            
            verification_time = time.time() - start_time
            logger.info(f"Attestation verification completed in {verification_time:.2f}s for {len(images)} images")
            
            if failed_images:
                full_message = f"Pod rejected. Failed images: {', '.join(failed_images)}\n" + "\n".join(verification_messages)
                logger.warning(f"Pod {pod_name} rejected: {len(failed_images)} images failed verification")
                return self.create_admission_response(
                    allowed=False,
                    message=full_message,
                    uid=uid
                )
            
            full_message = f"Pod allowed. All {len(images)} images passed attestation verification\n" + "\n".join(verification_messages)
            logger.info(f"Pod {pod_name} allowed: all images verified")
            return self.create_admission_response(
                allowed=True,
                message=full_message,
                uid=uid
            )
            
        except Exception as e:
            logger.error(f"Error validating pod: {str(e)}")
            return self.create_admission_response(
                allowed=False,
                message=f"Internal error during validation: {str(e)}",
                uid=admission_review.get("request", {}).get("uid", "")
            )

# Initialize the real admission controller
admission_controller = RealAdmissionController()

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "attestation-admission-controller"}), 200

@app.route("/validate", methods=["POST"])
def validate():
    """Main validation webhook endpoint"""
    try:
        # Parse the admission review request
        admission_review = request.get_json()
        
        if not admission_review:
            logger.error("Empty request body")
            return jsonify({"error": "Empty request body"}), 400
        
        logger.info(f"Received admission review: {admission_review.get('request', {}).get('uid', 'unknown')}")
        
        # Validate the pod
        response = admission_controller.validate_pod(admission_review)
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({
            "apiVersion": "admission.k8s.io/v1",
            "kind": "AdmissionReview", 
            "response": {
                "allowed": False,
                "status": {
                    "message": f"Internal server error: {str(e)}"
                }
            }
        }), 500

@app.route("/policy-summary", methods=["GET"])
def get_policy_summary():
    """Endpoint to view current policy configuration (for debugging)"""
    try:
        summary = admission_controller.policy_manager.get_policy_summary()
        return jsonify(summary), 200
    except Exception as e:
        logger.error(f"Error getting policy summary: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/policy-reload", methods=["POST"])
def reload_policy():
    """Endpoint to reload policy configuration"""
    try:
        admission_controller.policy_manager.reload_policy()
        return jsonify({"message": "Policy configuration reloaded successfully"}), 200
    except Exception as e:
        logger.error(f"Error reloading policy: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/clear-cache", methods=["POST"])
def clear_attestation_cache():
    """Endpoint to clear attestation verification cache"""
    try:
        admission_controller.attestation_verifier.clear_cache()
        return jsonify({"message": "Attestation cache cleared successfully"}), 200
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/verify-image", methods=["POST"])
def verify_image_endpoint():
    """Endpoint to manually verify image attestation (for testing)"""
    try:
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({"error": "Missing 'image' parameter"}), 400
        
        image = data['image']
        namespace = data.get('namespace', 'default')
        
        is_allowed, message = admission_controller.verify_image_attestation(image, namespace)
        
        return jsonify({
            "image": image,
            "namespace": namespace,
            "allowed": is_allowed,
            "message": message
        }), 200
        
    except Exception as e:
        logger.error(f"Error in manual verification: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    logger.info("Starting Real Image Attestation Admission Controller")
    policy_summary = admission_controller.policy_manager.get_policy_summary()
    logger.info(f"Policy configuration loaded: {policy_summary}")
    
    # Run the Flask app
    app.run(
        host="0.0.0.0",
        port=8443,
        ssl_context=("/certs/tls.crt", "/certs/tls.key"),  # Certificate and key files
        debug=False
    )
