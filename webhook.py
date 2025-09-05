#!/usr/bin/env python3
"""
Attestation-Driven Container Admission Controller
A Kubernetes ValidatingAdmissionWebhook that verifies container image attestations
"""

import json
import base64
import logging
from flask import Flask, request, jsonify
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Mock trusted images list (in production, this could come from a registry or attestation service)
TRUSTED_IMAGES = {
    "nginx:1.21",
    "nginx:latest", 
    "alpine:3.14",
    "alpine:latest",
    "python:3.9-slim",
    "busybox:latest",
    "hello-world:latest"
}

class AdmissionController:
    """Main admission controller class"""
    
    def __init__(self):
        self.trusted_images = TRUSTED_IMAGES
    
    def is_image_trusted(self, image: str) -> bool:
        """
        Check if an image is in the trusted images list
        In a real implementation, this would verify attestations
        """
        # Handle images with registry prefixes
        if "/" in image:
            image_parts = image.split("/")
            image_name = image_parts[-1]  # Get the last part (image:tag)
        else:
            image_name = image
        
        logger.info(f"Checking image: {image_name}")
        return image_name in self.trusted_images
    
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
        """Main validation logic for pods"""
        try:
            # Extract the pod object from the admission request
            request_info = admission_review.get("request", {})
            pod = request_info.get("object", {})
            uid = request_info.get("uid", "")
            
            logger.info(f"Validating pod: {pod.get('metadata', {}).get('name', 'unknown')}")
            
            # Extract all images from the pod
            images = self.extract_images_from_pod(pod)
            
            if not images:
                return self.create_admission_response(
                    allowed=True, 
                    message="No images found in pod specification", 
                    uid=uid
                )
            
            # Check each image
            untrusted_images = []
            for image in images:
                if not self.is_image_trusted(image):
                    untrusted_images.append(image)
            
            if untrusted_images:
                message = f"Pod rejected: Untrusted images detected: {', '.join(untrusted_images)}"
                logger.warning(message)
                return self.create_admission_response(
                    allowed=False,
                    message=message,
                    uid=uid
                )
            
            message = f"Pod allowed: All images are trusted: {', '.join(images)}"
            logger.info(message)
            return self.create_admission_response(
                allowed=True,
                message=message,
                uid=uid
            )
            
        except Exception as e:
            logger.error(f"Error validating pod: {str(e)}")
            return self.create_admission_response(
                allowed=False,
                message=f"Internal error during validation: {str(e)}",
                uid=admission_review.get("request", {}).get("uid", "")
            )

# Initialize the admission controller
admission_controller = AdmissionController()

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

@app.route("/trusted-images", methods=["GET"])
def get_trusted_images():
    """Endpoint to view current trusted images (for debugging)"""
    return jsonify({
        "trusted_images": list(admission_controller.trusted_images),
        "count": len(admission_controller.trusted_images)
    }), 200

if __name__ == "__main__":
    logger.info("Starting Attestation-Driven Admission Controller")
    logger.info(f"Trusted images: {len(TRUSTED_IMAGES)} images configured")
    
    # Run the Flask app
    app.run(
        host="0.0.0.0",
        port=8443,
        ssl_context=("/certs/tls.crt", "/certs/tls.key"),  # Certificate and key files
        debug=False
    )
