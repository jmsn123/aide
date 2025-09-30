#!/bin/bash
set -e

# Python Minifier Helper Script
# Removes comments and docstrings from Python files for production deployment

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[MINIFY]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[MINIFY]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[MINIFY]${NC} $1"
}

log_error() {
    echo -e "${RED}[MINIFY]${NC} $1"
}

# Check if python-minifier is available
check_minifier() {
    # Check if python-minifier module is available
    if python3 -c "import python_minifier" &> /dev/null; then
        log_info "python-minifier module is available"
        return 0
    fi

    log_info "python-minifier not found, installing..."

    # Try different installation methods
    if command -v pip3 &> /dev/null; then
        pip3 install python-minifier --user --quiet 2>/dev/null || \
        pip3 install python-minifier --break-system-packages --quiet 2>/dev/null
    elif command -v pip &> /dev/null; then
        pip install python-minifier --user --quiet 2>/dev/null || \
        pip install python-minifier --break-system-packages --quiet 2>/dev/null
    fi

    # Check if installation was successful
    if python3 -c "import python_minifier" &> /dev/null; then
        log_success "python-minifier installed successfully"
    else
        log_error "Failed to install python-minifier"
        log_error "Please install manually: pip3 install python-minifier --break-system-packages"
        return 1
    fi
}

# Enhanced minify function that safely removes comments and docstrings
minify_file() {
    local input_file="$1"
    local temp_file="${input_file}.tmp"
    local preprocessed_file="${input_file}.prep"

    if [[ ! -f "$input_file" ]]; then
        log_warning "File not found: $input_file"
        return 1
    fi

    log_info "Minifying: $(basename "$input_file")"

    # Calculate original size
    local original_size=$(stat -f%z "$input_file" 2>/dev/null || stat -c%s "$input_file" 2>/dev/null || echo "0")

    # Step 1: Check if file contains f-strings (comprehensive detection)
    local has_fstrings=false
    if grep -Eq "f[\"']|f\"\"\"|f'''|F[\"']|F\"\"\"|F'''" "$input_file"; then
        has_fstrings=true
        log_info "  Detected f-strings, using ultra-safe mode with no variable renaming"
    fi

    # Step 2: Pre-process to remove comments and docstrings safely
    python3 -c "
import re
import sys

def safe_remove_docs_and_comments(source):
    '''Safely remove comments and docstrings while preserving f-strings'''
    lines = source.split('\n')
    result_lines = []

    for line in lines:
        stripped = line.strip()

        # Remove full-line comments
        if stripped.startswith('#'):
            result_lines.append('')
            continue

        # Remove standalone docstrings (simple heuristic)
        if (stripped.startswith('\"\"\"') and stripped.endswith('\"\"\"') and len(stripped) > 6) or \
           (stripped.startswith(\"'''\") and stripped.endswith(\"'''\") and len(stripped) > 6):
            result_lines.append('')
            continue

        # Remove inline comments while preserving f-strings
        if '#' in line:
            # Simple approach: find # that's not inside quotes
            in_quotes = False
            quote_char = None
            comment_pos = -1

            i = 0
            while i < len(line):
                char = line[i]

                if not in_quotes:
                    if char in ['\"', \"'\"]:
                        quote_char = char
                        in_quotes = True
                    elif char == '#':
                        comment_pos = i
                        break
                else:
                    if char == quote_char and (i == 0 or line[i-1] != '\\\\'):
                        in_quotes = False
                        quote_char = None

                i += 1

            if comment_pos >= 0:
                line = line[:comment_pos].rstrip()

        result_lines.append(line)

    return '\n'.join(result_lines)

# Read and process file
try:
    with open('$input_file', 'r', encoding='utf-8') as f:
        source = f.read()

    processed = safe_remove_docs_and_comments(source)

    with open('$preprocessed_file', 'w', encoding='utf-8') as f:
        f.write(processed)

except Exception as e:
    print(f'Error: {e}', file=sys.stderr)
    sys.exit(1)
"

    if [ $? -ne 0 ]; then
        log_warning "  Pre-processing failed, using original file"
        cp "$input_file" "$preprocessed_file"
    fi

    # Step 3: Apply python-minifier with appropriate settings
    local minifier_success=false

    if [ "$has_fstrings" = true ]; then
        # Ultra-safe mode for f-strings - disable all variable renaming and dangerous transformations
        log_info "  Applying f-string ultra-safe minification (no variable renaming)..."
        python3 -m python_minifier \
            --no-combine-imports \
            --no-remove-annotations \
            --no-hoist-literals \
            --no-rename-locals \
            --no-constant-folding \
            --no-remove-builtin-exception-brackets \
            --no-convert-posargs-to-args \
            --remove-literal-statements \
            --output "$temp_file" \
            "$preprocessed_file" && minifier_success=true
    else
        # More aggressive mode for files without f-strings
        log_info "  Applying aggressive minification..."
        python3 -m python_minifier \
            --remove-literal-statements \
            --no-combine-imports \
            --no-remove-annotations \
            --no-hoist-literals \
            --no-rename-locals \
            --no-constant-folding \
            --output "$temp_file" \
            "$preprocessed_file" && minifier_success=true
    fi

    # Step 4: Validate and finalize
    if [ "$minifier_success" = true ] && [ -s "$temp_file" ]; then
        # Validate syntax of minified file
        if python3 -c "import ast; ast.parse(open('$temp_file').read())" 2>/dev/null; then
            # Calculate size reduction
            local new_size=$(stat -f%z "$temp_file" 2>/dev/null || stat -c%s "$temp_file" 2>/dev/null || echo "0")
            local reduction_percent=0

            if [ "$original_size" -gt 0 ]; then
                reduction_percent=$(( (original_size - new_size) * 100 / original_size ))
            fi

            # Success - use minified version
            mv "$temp_file" "$input_file"
            log_success "  Enhanced minification: ${reduction_percent}% reduction (${original_size} → ${new_size} bytes)"
        else
            log_warning "  Minified file has syntax errors, using preprocessed version"
            # Fallback to preprocessed version (comments/docstrings removed, but not minified)
            local preprocessed_size=$(stat -f%z "$preprocessed_file" 2>/dev/null || stat -c%s "$preprocessed_file" 2>/dev/null || echo "0")
            local reduction_percent=0

            if [ "$original_size" -gt 0 ]; then
                reduction_percent=$(( (original_size - preprocessed_size) * 100 / original_size ))
            fi

            mv "$preprocessed_file" "$input_file"
            log_info "  Used preprocessed version: ${reduction_percent}% reduction (${original_size} → ${preprocessed_size} bytes)"
        fi
    else
        log_error "  Minification failed, keeping original"
        # Don't modify the original file
    fi

    # Cleanup temporary files
    rm -f "$temp_file" "$preprocessed_file"
}

# Minify all Python files in a directory
minify_directory() {
    local target_dir="$1"

    if [[ ! -d "$target_dir" ]]; then
        log_warning "Directory not found: $target_dir"
        return 1
    fi

    log_info "Minifying Python files in: $target_dir"

    local file_count=0
    local success_count=0

    # Find all Python files and minify them
    # Skip files with known f-string nested quote issues
    while IFS= read -r -d '' file; do
        local filename=$(basename "$file")

        # Skip files known to have f-string quote nesting issues
        if [[ "$filename" == "metadata_extractor.py" ]] || [[ "$filename" == "pdf_utils.py" ]]; then
            log_warning "Skipping $filename (f-string nested quote handling)"
            continue
        fi

        ((file_count++))
        if minify_file "$file"; then
            ((success_count++))
        fi
    done < <(find "$target_dir" -name "*.py" -type f -print0)

    if [ "$file_count" -eq 0 ]; then
        log_warning "No Python files found in $target_dir"
    else
        log_success "Minified $success_count/$file_count Python files in $(basename "$target_dir")"
    fi
}

# Main function
main() {
    local target="$1"

    if [[ -z "$target" ]]; then
        log_error "Usage: $0 <file_or_directory>"
        log_error "Examples:"
        log_error "  $0 /path/to/file.py"
        log_error "  $0 /path/to/directory"
        exit 1
    fi

    # Check prerequisites
    check_minifier || exit 1

    if [[ -f "$target" ]]; then
        # Single file
        minify_file "$target"
    elif [[ -d "$target" ]]; then
        # Directory
        minify_directory "$target"
    else
        log_error "Target not found: $target"
        exit 1
    fi
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi