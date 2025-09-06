#!/bin/bash
"""
Container Image Signing Tool
Sign container images using Cosign for use with the attestation admission controller
"""

set -e

# Configuration
COSIGN_PRIVATE_KEY_FILE=${COSIGN_PRIVATE_KEY_FILE:-"cosign.key"}
COSIGN_PUBLIC_KEY_FILE=${COSIGN_PUBLIC_KEY_FILE:-"cosign.pub"}
COSIGN_PASSWORD=${COSIGN_PASSWORD:-""}
DEFAULT_REGISTRY=${DEFAULT_REGISTRY:-"docker.io"}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_dependencies() {
    log_info "Checking dependencies..."
    
    if ! command -v cosign &> /dev/null; then
        log_error "cosign is not installed. Please install cosign first."
        log_info "Installation: go install github.com/sigstore/cosign/v2/cmd/cosign@latest"
        exit 1
    fi
    
    if ! command -v docker &> /dev/null; then
        log_error "docker is not installed. Please install Docker first."
        exit 1
    fi
    
    log_info "Dependencies check passed"
}

generate_keypair() {
    log_info "Generating Cosign key pair..."
    
    if [[ -f "$COSIGN_PRIVATE_KEY_FILE" ]] || [[ -f "$COSIGN_PUBLIC_KEY_FILE" ]]; then
        log_warn "Key files already exist. Do you want to overwrite them? (y/N)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            log_info "Keeping existing keys"
            return 0
        fi
    fi
    
    if [[ -z "$COSIGN_PASSWORD" ]]; then
        cosign generate-key-pair
    else
        echo "$COSIGN_PASSWORD" | cosign generate-key-pair
    fi
    
    log_info "Key pair generated:"
    log_info "  Private key: $COSIGN_PRIVATE_KEY_FILE"
    log_info "  Public key: $COSIGN_PUBLIC_KEY_FILE"
}

sign_image() {
    local image="$1"
    
    if [[ -z "$image" ]]; then
        log_error "Image name is required"
        show_usage
        exit 1
    fi
    
    # Add default registry if not specified
    if [[ ! "$image" == *"/"* ]]; then
        image="$DEFAULT_REGISTRY/library/$image"
    elif [[ ! "$image" == *"."* ]] && [[ ! "$image" == *":"* ]] && [[ "$image" == *"/"* ]]; then
        image="$DEFAULT_REGISTRY/$image"
    fi
    
    log_info "Signing image: $image"
    
    # Check if keys exist
    if [[ ! -f "$COSIGN_PRIVATE_KEY_FILE" ]]; then
        log_error "Private key file not found: $COSIGN_PRIVATE_KEY_FILE"
        log_info "Generate keys first with: $0 generate-keys"
        exit 1
    fi
    
    # Sign the image
    if [[ -z "$COSIGN_PASSWORD" ]]; then
        cosign sign --key "$COSIGN_PRIVATE_KEY_FILE" "$image"
    else
        echo "$COSIGN_PASSWORD" | cosign sign --key "$COSIGN_PRIVATE_KEY_FILE" "$image"
    fi
    
    log_info "Image signed successfully: $image"
    log_info "Signature can be verified with public key: $COSIGN_PUBLIC_KEY_FILE"
}

verify_image() {
    local image="$1"
    
    if [[ -z "$image" ]]; then
        log_error "Image name is required"
        show_usage
        exit 1
    fi
    
    # Add default registry if not specified
    if [[ ! "$image" == *"/"* ]]; then
        image="$DEFAULT_REGISTRY/library/$image"
    elif [[ ! "$image" == *"."* ]] && [[ ! "$image" == *":"* ]] && [[ "$image" == *"/"* ]]; then
        image="$DEFAULT_REGISTRY/$image"
    fi
    
    log_info "Verifying image: $image"
    
    # Check if public key exists
    if [[ ! -f "$COSIGN_PUBLIC_KEY_FILE" ]]; then
        log_error "Public key file not found: $COSIGN_PUBLIC_KEY_FILE"
        exit 1
    fi
    
    # Verify the signature
    if cosign verify --key "$COSIGN_PUBLIC_KEY_FILE" "$image"; then
        log_info "✅ Image signature verification PASSED: $image"
    else
        log_error "❌ Image signature verification FAILED: $image"
        exit 1
    fi
}

sign_with_attestation() {
    local image="$1"
    local attestation_file="$2"
    
    if [[ -z "$image" ]] || [[ -z "$attestation_file" ]]; then
        log_error "Both image name and attestation file are required"
        show_usage
        exit 1
    fi
    
    if [[ ! -f "$attestation_file" ]]; then
        log_error "Attestation file not found: $attestation_file"
        exit 1
    fi
    
    # Add default registry if not specified
    if [[ ! "$image" == *"/"* ]]; then
        image="$DEFAULT_REGISTRY/library/$image"
    elif [[ ! "$image" == *"."* ]] && [[ ! "$image" == *":"* ]] && [[ "$image" == *"/"* ]]; then
        image="$DEFAULT_REGISTRY/$image"
    fi
    
    log_info "Signing image with attestation: $image"
    log_info "Attestation file: $attestation_file"
    
    # Check if keys exist
    if [[ ! -f "$COSIGN_PRIVATE_KEY_FILE" ]]; then
        log_error "Private key file not found: $COSIGN_PRIVATE_KEY_FILE"
        log_info "Generate keys first with: $0 generate-keys"
        exit 1
    fi
    
    # Sign with attestation
    if [[ -z "$COSIGN_PASSWORD" ]]; then
        cosign attest --key "$COSIGN_PRIVATE_KEY_FILE" --predicate "$attestation_file" "$image"
    else
        echo "$COSIGN_PASSWORD" | cosign attest --key "$COSIGN_PRIVATE_KEY_FILE" --predicate "$attestation_file" "$image"
    fi
    
    log_info "Image signed with attestation successfully: $image"
}

keyless_sign() {
    local image="$1"
    
    if [[ -z "$image" ]]; then
        log_error "Image name is required"
        show_usage
        exit 1
    fi
    
    # Add default registry if not specified
    if [[ ! "$image" == *"/"* ]]; then
        image="$DEFAULT_REGISTRY/library/$image"
    elif [[ ! "$image" == *"."* ]] && [[ ! "$image" == *":"* ]] && [[ "$image" == *"/"* ]]; then
        image="$DEFAULT_REGISTRY/$image"
    fi
    
    log_info "Signing image with keyless signature (OIDC): $image"
    log_warn "This will require browser authentication via OIDC provider"
    
    # Keyless signing
    cosign sign "$image"
    
    log_info "Image signed successfully with keyless signature: $image"
    log_info "Signature is stored in transparency log and can be verified without a key"
}

show_usage() {
    cat << EOF
Container Image Signing Tool

Usage: $0 <command> [options]

Commands:
    generate-keys                   Generate Cosign key pair
    sign <image>                   Sign container image
    verify <image>                 Verify container image signature
    sign-with-attestation <image> <attestation-file>
                                   Sign image with SLSA provenance attestation
    keyless-sign <image>           Sign image using keyless (OIDC) flow
    
Environment Variables:
    COSIGN_PRIVATE_KEY_FILE        Path to private key (default: cosign.key)
    COSIGN_PUBLIC_KEY_FILE         Path to public key (default: cosign.pub)
    COSIGN_PASSWORD               Password for private key (optional)
    DEFAULT_REGISTRY              Default registry (default: docker.io)

Examples:
    # Generate keys
    $0 generate-keys
    
    # Sign an image
    $0 sign nginx:latest
    $0 sign myregistry.io/myapp:v1.0.0
    
    # Verify an image
    $0 verify nginx:latest
    
    # Sign with attestation
    $0 sign-with-attestation myapp:latest slsa-provenance.json
    
    # Keyless signing
    $0 keyless-sign nginx:latest

EOF
}

# Main script
main() {
    case "$1" in
        "generate-keys")
            check_dependencies
            generate_keypair
            ;;
        "sign")
            check_dependencies
            sign_image "$2"
            ;;
        "verify")
            check_dependencies
            verify_image "$2"
            ;;
        "sign-with-attestation")
            check_dependencies
            sign_with_attestation "$2" "$3"
            ;;
        "keyless-sign")
            check_dependencies
            keyless_sign "$2"
            ;;
        "help"|"-h"|"--help")
            show_usage
            ;;
        "")
            log_error "No command specified"
            show_usage
            exit 1
            ;;
        *)
            log_error "Unknown command: $1"
            show_usage
            exit 1
            ;;
    esac
}

main "$@"
