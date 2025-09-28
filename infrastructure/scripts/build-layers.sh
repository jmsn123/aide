#!/bin/bash
set -e

# PDF Extractor API - Lambda Layers Build Script
# This script builds all Lambda layers for the PDF Extractor API
#
# STRICT BUILD POLICY:
# - NO FALLBACKS: If platform-specific install fails, the build FAILS
# - MANDATORY VALIDATION: Cryptography dependency is validated post-install
# - LAMBDA COMPATIBILITY: All dependencies MUST be built for manylinux2014_x86_64
# - FAIL-FAST: Any missing critical dependency causes immediate build failure
#
# This ensures encrypted PDF processing works reliably in Lambda runtime

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
INFRA_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
API_ROOT="$PROJECT_ROOT/api"
LAYERS_DIR="$INFRA_ROOT/layers"
OUTPUT_DIR="$INFRA_ROOT/lambda_packages/layers"
PYTHON_VERSION="python3"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check Python version
    if ! command -v $PYTHON_VERSION &> /dev/null; then
        log_error "Python 3.11 is required but not found. Please install Python 3.11."
        exit 1
    fi

    # Check pip (prefer pip3 if available)
    if command -v pip3 &> /dev/null; then
        PIP_CMD="pip3"
    elif command -v pip &> /dev/null; then
        PIP_CMD="pip"
    else
        log_error "pip or pip3 is required but not found. Please install pip."
        exit 1
    fi

    # Check zip
    if ! command -v zip &> /dev/null; then
        log_error "zip is required but not found. Please install zip."
        exit 1
    fi

    log_success "All prerequisites met"
}

# Validate critical dependencies in layer
validate_cryptography_installation() {
    local python_dir="$1"
    local layer_name="$2"

    log_info "Validating cryptography installation in $layer_name..."

    # Check if cryptography package exists
    if [[ ! -d "$python_dir/cryptography" ]]; then
        log_error "Cryptography package not found in $layer_name layer!"
        log_error "This is a CRITICAL dependency for PDF encryption support."
        exit 1
    fi

    # Check if CFFI (cryptography backend) exists
    if [[ ! -f "$python_dir/cffi/__init__.py" ]] && [[ ! -f "$python_dir/_cffi_backend.py" ]]; then
        log_error "CFFI backend not found in $layer_name layer!"
        log_error "This is REQUIRED for cryptography to function in Lambda."
        exit 1
    fi

    # Check for the critical shared library
    if ! find "$python_dir" -name "*.so" -path "*/cryptography/*" | head -1 | grep -q "cryptography"; then
        log_error "Cryptography shared libraries not found in $layer_name layer!"
        log_error "Platform-specific build may have failed."
        exit 1
    fi

    log_success "Cryptography validation passed for $layer_name layer"
}

# Clean output directory
clean_output() {
    log_info "Cleaning output directory..."
    rm -rf "$OUTPUT_DIR"
    mkdir -p "$OUTPUT_DIR"
    log_success "Output directory cleaned"
}

# Build common dependencies layer
build_common_layer() {
    log_info "Building common dependencies layer..."
    
    local layer_name="pdf-extractor-common"
    local layer_dir="$LAYERS_DIR/common-dependencies"
    local build_dir="$OUTPUT_DIR/${layer_name}-build"
    local python_dir="$build_dir/python/lib/python3.11/site-packages"
    
    # Create build directory
    mkdir -p "$python_dir"
    
    # Install dependencies for Lambda (manylinux compatible) - MANDATORY, no fallback
    log_info "Installing common dependencies with platform-specific build..."
    if ! $PIP_CMD install -r "$layer_dir/requirements.txt" -t "$python_dir" \
        --platform manylinux2014_x86_64 \
        --implementation cp \
        --python-version 3.11 \
        --abi cp311 \
        --no-deps \
        --no-cache-dir \
        --disable-pip-version-check; then
        log_error "Failed to install dependencies with platform specification. This is REQUIRED for Lambda compatibility."
        log_error "Ensure you have an internet connection and all dependencies are available for manylinux2014_x86_64."
        exit 1
    fi

    # Validate critical cryptography installation
    validate_cryptography_installation "$python_dir" "common-dependencies"

    # Remove unnecessary files to reduce size
    log_info "Optimizing layer size..."
    find "$python_dir" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$python_dir" -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
    find "$python_dir" -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
    find "$python_dir" -name "*.pyc" -delete 2>/dev/null || true
    find "$python_dir" -name "*.pyo" -delete 2>/dev/null || true
    
    # Create zip file
    log_info "Creating layer zip file..."
    cd "$build_dir"
    zip -r9 "$OUTPUT_DIR/${layer_name}.zip" python/ > /dev/null
    cd - > /dev/null
    
    # Cleanup build directory
    rm -rf "$build_dir"
    
    local zip_size=$(du -h "$OUTPUT_DIR/${layer_name}.zip" | cut -f1)
    log_success "Common dependencies layer created: ${layer_name}.zip (${zip_size})"
}

# Build API dependencies layer  
build_api_layer() {
    log_info "Building API dependencies layer..."
    
    local layer_name="pdf-extractor-api"
    local layer_dir="$LAYERS_DIR/api-dependencies"
    local build_dir="$OUTPUT_DIR/${layer_name}-build"
    local python_dir="$build_dir/python/lib/python3.11/site-packages"
    
    # Create build directory
    mkdir -p "$python_dir"
    
    # Install dependencies for Lambda (manylinux compatible) - MANDATORY, no fallback
    log_info "Installing API dependencies with platform-specific build..."
    if ! $PIP_CMD install -r "$layer_dir/requirements.txt" -t "$python_dir" \
        --platform manylinux2014_x86_64 \
        --implementation cp \
        --python-version 3.11 \
        --abi cp311 \
        --no-deps \
        --no-cache-dir \
        --disable-pip-version-check; then
        log_error "Failed to install API dependencies with platform specification. This is REQUIRED for Lambda compatibility."
        log_error "Ensure you have an internet connection and all dependencies are available for manylinux2014_x86_64."
        exit 1
    fi
    
    # Remove unnecessary files to reduce size
    log_info "Optimizing layer size..."
    find "$python_dir" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$python_dir" -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
    find "$python_dir" -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
    find "$python_dir" -name "*.pyc" -delete 2>/dev/null || true
    find "$python_dir" -name "*.pyo" -delete 2>/dev/null || true
    
    # Create zip file
    log_info "Creating layer zip file..."
    cd "$build_dir"
    zip -r9 "$OUTPUT_DIR/${layer_name}.zip" python/ > /dev/null
    cd - > /dev/null
    
    # Cleanup build directory
    rm -rf "$build_dir"
    
    local zip_size=$(du -h "$OUTPUT_DIR/${layer_name}.zip" | cut -f1)
    log_success "API dependencies layer created: ${layer_name}.zip (${zip_size})"
}

# Build business logic layer
build_business_layer() {
    log_info "Building business logic layer..."
    
    local layer_name="pdf-extractor-business"
    local layer_dir="$LAYERS_DIR/business-logic"
    local build_dir="$OUTPUT_DIR/${layer_name}-build"
    local python_dir="$build_dir/python"
    
    # Create build directory
    mkdir -p "$python_dir"
    
    # Install dependencies if requirements.txt exists
    if [[ -f "$layer_dir/requirements.txt" ]]; then
        local site_packages_dir="$python_dir/lib/python3.11/site-packages"
        mkdir -p "$site_packages_dir"
        log_info "Installing business logic dependencies with platform-specific build..."
        if ! $PIP_CMD install -r "$layer_dir/requirements.txt" -t "$site_packages_dir" \
            --platform manylinux2014_x86_64 \
            --implementation cp \
            --python-version 3.11 \
            --abi cp311 \
            --no-deps \
            --no-cache-dir \
            --disable-pip-version-check; then
            log_error "Failed to install business logic dependencies with platform specification. This is REQUIRED for Lambda compatibility."
            log_error "Ensure you have an internet connection and all dependencies are available for manylinux2014_x86_64."
            exit 1
        fi

        # Remove unnecessary files to reduce size
        log_info "Optimizing business layer size..."
        find "$site_packages_dir" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        find "$site_packages_dir" -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
        find "$site_packages_dir" -name "*.pyc" -delete 2>/dev/null || true
    fi

    # Copy business logic modules
    log_info "Copying business logic modules..."
    cp "$API_ROOT/config.py" "$python_dir/"
    cp "$API_ROOT/logging_config.py" "$python_dir/"
    cp "$API_ROOT/extract_pdf_data.py" "$python_dir/"
    cp "$API_ROOT/bank_config.py" "$python_dir/"

    # Minify business logic files for production
    log_info "Minifying business logic files for production deployment..."
    "$SCRIPT_DIR/minify-python.sh" "$python_dir/config.py"
    "$SCRIPT_DIR/minify-python.sh" "$python_dir/logging_config.py"
    # Skip minification for files with complex f-string usage until better solution
    log_info "  Skipping minification for extract_pdf_data.py and bank_config.py (f-string quote handling)"

    # Copy formatters directory if it exists
    if [[ -d "$API_ROOT/formatters" ]]; then
        log_info "Copying formatters directory..."
        cp -r "$API_ROOT/formatters" "$python_dir/"
    fi

    # Copy extractors directory if it exists
    if [[ -d "$API_ROOT/extractors" ]]; then
        log_info "Copying extractors directory..."
        cp -r "$API_ROOT/extractors" "$python_dir/"

        # Minify Python files in extractors for production
        log_info "Minifying extractor files for production deployment..."
        "$SCRIPT_DIR/minify-python.sh" "$python_dir/extractors"
    fi

    # Copy validators directory if it exists
    if [[ -d "$API_ROOT/validators" ]]; then
        log_info "Copying validators directory..."
        cp -r "$API_ROOT/validators" "$python_dir/"
    fi


    # Create __init__.py files to make it a proper Python package
    touch "$python_dir/__init__.py"
    
    # Create zip file
    log_info "Creating layer zip file..."
    cd "$build_dir"
    zip -r9 "$OUTPUT_DIR/${layer_name}.zip" python/ > /dev/null
    cd - > /dev/null
    
    # Cleanup build directory
    rm -rf "$build_dir"
    
    local zip_size=$(du -h "$OUTPUT_DIR/${layer_name}.zip" | cut -f1)
    log_success "Business logic layer created: ${layer_name}.zip (${zip_size})"
}

# Build all layers
build_all_layers() {
    log_info "Starting Lambda layers build process..."
    log_info "*** STRICT BUILD MODE: No fallbacks, platform-specific dependencies only ***"
    log_info "*** This ensures Lambda compatibility and prevents runtime errors ***"

    check_prerequisites
    clean_output
    
    build_common_layer
    build_api_layer
    build_business_layer
    
    log_info "Build summary:"
    ls -lh "$OUTPUT_DIR"/*.zip | while read -r line; do
        log_info "  $(echo "$line" | awk '{print $9 " - " $5}')"
    done
    
    # Final validation of critical layers
    log_info "Performing final validation of all layers..."

    # Validate common layer has cryptography
    local common_zip="$OUTPUT_DIR/pdf-extractor-common.zip"
    if [[ -f "$common_zip" ]]; then
        local temp_dir=$(mktemp -d)
        unzip -q "$common_zip" -d "$temp_dir"
        validate_cryptography_installation "$temp_dir/python/lib/python3.11/site-packages" "final-common-layer"
        rm -rf "$temp_dir"
        log_success "Final validation passed for common layer"
    else
        log_error "Common layer zip file not found: $common_zip"
        exit 1
    fi

    log_success "All Lambda layers built successfully!"
    log_success "All layers have been validated for Lambda compatibility!"
    log_info "Layer files are available in: $OUTPUT_DIR"
}

# Main execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    build_all_layers
fi