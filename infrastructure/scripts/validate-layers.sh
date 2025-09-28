#!/bin/bash
set -e

# PDF Extractor API - Lambda Layers Validation Script
# This script validates that Lambda layers contain required dependencies

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[VALIDATE]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LAYERS_DIR="$INFRA_ROOT/lambda_packages/layers"

validate_layer() {
    local layer_zip="$1"
    local layer_name="$2"
    local expected_packages=("${@:3}")

    log_info "Validating $layer_name..."

    if [[ ! -f "$layer_zip" ]]; then
        log_error "Layer zip not found: $layer_zip"
        return 1
    fi

    # Create temporary directory for extraction
    local temp_dir=$(mktemp -d)
    trap "rm -rf $temp_dir" EXIT

    # Extract layer
    unzip -q "$layer_zip" -d "$temp_dir"

    # Find Python packages directory
    local python_packages_dir=""
    if [[ -d "$temp_dir/python/lib/python3.11/site-packages" ]]; then
        python_packages_dir="$temp_dir/python/lib/python3.11/site-packages"
    elif [[ -d "$temp_dir/python" ]]; then
        python_packages_dir="$temp_dir/python"
    else
        log_error "Python packages directory not found in $layer_name"
        return 1
    fi

    # Check for expected packages
    for package in "${expected_packages[@]}"; do
        if [[ -d "$python_packages_dir/$package" ]] || [[ -f "$python_packages_dir/${package}.py" ]]; then
            log_success "  ✓ $package found"
        else
            log_error "  ✗ $package NOT found"
            return 1
        fi
    done

    # Special validation for cryptography (if present)
    if [[ " ${expected_packages[@]} " =~ " cryptography " ]]; then
        log_info "  Performing cryptography validation..."

        # Check for CFFI
        if [[ -d "$python_packages_dir/cffi" ]] || [[ -f "$python_packages_dir/_cffi_backend.py" ]]; then
            log_success "  ✓ CFFI backend found"
        else
            log_error "  ✗ CFFI backend NOT found"
            return 1
        fi

        # Check for shared libraries
        if find "$python_packages_dir" -name "*.so" -path "*/cryptography/*" | head -1 | grep -q "cryptography"; then
            log_success "  ✓ Cryptography shared libraries found"
        else
            log_error "  ✗ Cryptography shared libraries NOT found"
            return 1
        fi

        log_success "  ✓ Cryptography validation passed"
    fi

    log_success "$layer_name validation passed"
    return 0
}

main() {
    log_info "Starting Lambda layers validation..."

    # Validate common dependencies layer
    validate_layer \
        "$LAYERS_DIR/pdf-extractor-common.zip" \
        "Common Dependencies" \
        "cryptography" "cffi" "pypdf" "openpyxl" "magic"

    # Validate API dependencies layer
    validate_layer \
        "$LAYERS_DIR/pdf-extractor-api.zip" \
        "API Dependencies" \
        "fastapi" "uvicorn" "mangum" "httpx"

    # Validate business logic layer
    validate_layer \
        "$LAYERS_DIR/pdf-extractor-business.zip" \
        "Business Logic" \
        "pydantic" "aws_lambda_powertools"

    log_success "All layer validations passed!"
    log_info "Layers are ready for Lambda deployment"
}

# Run main function
main "$@"