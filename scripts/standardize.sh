#!/usr/bin/env bash
# ============================================================================
# latex-standardizer: Best-effort LaTeX .tex source formatting
#
# Pipeline (per file):
#   1. Post-processing (best-effort: sentence splitting, blank lines,
#      preamble grouping)
#   2. latexindent (deterministic: indent, whitespace, environment alignment)
#   3. AASTeX v7 validation (auto-detected: deprecated commands, forbidden
#      packages, structural metadata checks)
#
# Usage:
#   standardize.sh [--check] [--in-place] <file.tex> [<file2.tex> ...]
#   standardize.sh --help
#
#   --check       Dry-run: report violations, exit non-zero if any found
#   --in-place    Overwrite files (required for actual formatting)
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_YAML="${SKILL_DIR}/references/latex-standardizer.yaml"
POST_PROCESSOR="${SKILL_DIR}/scripts/_post_process.py"
AASTEX_VALIDATOR="${SKILL_DIR}/scripts/_aastex_validate.py"

# Colors for output
RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
NC=$'\033[0m' # No Color

CHECK_MODE=false
IN_PLACE=false
FILES=()
HAS_AASTEX=false

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS] <file.tex> [<file2.tex> ...]

Options:
  --check       Dry-run: report violations, exit non-zero if found
  --in-place    Overwrite files with formatted output
  --help        Show this message
EOF
    exit 0
}

# --- Parse arguments ---
while [[ $# -gt 0 ]]; do
    case "$1" in
        --check)   CHECK_MODE=true; shift ;;
        --in-place) IN_PLACE=true; shift ;;
        --help)    usage ;;
        -*)        echo "Unknown option: $1"; usage ;;
        *)         FILES+=("$1"); shift ;;
    esac
done

if [[ ${#FILES[@]} -eq 0 ]]; then
    echo "Error: No .tex files specified."
    usage
fi

# --- Check dependencies ---
if ! command -v latexindent &>/dev/null; then
    echo "Error: latexindent not found. Install with:"
    echo "  sudo cpan App::latexindent"
    echo "  or: sudo apt install latexindent"
    exit 1
fi

if ! command -v python3 &>/dev/null; then
    echo "Error: python3 not found."
    exit 1
fi

# Ensure post-processor exists
if [[ ! -f "$POST_PROCESSOR" ]]; then
    echo "Error: Post-processor not found: $POST_PROCESSOR"
    exit 1
fi

if [[ ! -f "$CONFIG_YAML" ]]; then
    echo "Error: Config not found: $CONFIG_YAML"
    exit 1
fi

# --- Helper: detect AASTeX v7 document class ---
is_aastex_file() {
    grep -q '\\documentclass.*{aastex7' "$1" 2>/dev/null
}

# --- Detect if any file is AASTeX v7 (for header) ---
for f in "${FILES[@]}"; do
    if is_aastex_file "$f"; then
        HAS_AASTEX=true
        break
    fi
done

# --- Core function: format one file (PP → latexindent → AASTeX v7, single pass) ---
run_pipeline() {
    local texfile="$1"
    python3 "$POST_PROCESSOR" --in-place "$texfile" "$CONFIG_YAML" || return 1
    latexindent -l="$CONFIG_YAML" -s -w "$texfile" 2>/dev/null || true
    if is_aastex_file "$texfile"; then
        python3 "$AASTEX_VALIDATOR" --in-place "$texfile" 2>/dev/null || true
    fi
    return 0
}

# --- Core function: process one file ---
process_file() {
    local texfile="$1"
    local violations=0

    if [[ ! -f "$texfile" ]]; then
        echo "${RED}Error:${NC} File not found: $texfile"
        return 1
    fi

    echo "  Processing: $texfile"

    # Encoding check
    if ! python3 -c "
import sys
try:
    with open('$texfile', 'rb') as f:
        raw = f.read()
    raw.decode('utf-8')
except UnicodeDecodeError:
    sys.exit(1)
" 2>/dev/null; then
        echo "    ${YELLOW}[WARN]${NC} File is not valid UTF-8"
        ((violations++))
    fi

    if $CHECK_MODE; then
        tmpfile=$(mktemp)
        cp "$texfile" "$tmpfile"
        run_pipeline "$tmpfile" || true
        if ! diff -q "$texfile" "$tmpfile" &>/dev/null; then
            echo "    ${YELLOW}[FAIL]${NC} File would be modified by formatting"
            ((violations++))
        fi
        if is_aastex_file "$texfile"; then
            aastex_out=$(python3 "$AASTEX_VALIDATOR" --check "$tmpfile" 2>&1) || true
            if [[ -n "$aastex_out" ]]; then
                echo "$aastex_out"
                # Count error-level violations (lines with [ERROR])
                aastex_errors=$(echo "$aastex_out" | grep -c '\[ERROR\]' || true)
                violations=$((violations + aastex_errors))
            fi
        fi
        rm -f "$tmpfile"
    elif $IN_PLACE; then
        run_pipeline "$texfile" || {
            echo "    ${RED}[FAIL]${NC} Pipeline failed"
            return 1
        }
        echo "    ${GREEN}[OK]${NC} Formatting applied (PP→latexindent)"
        if is_aastex_file "$texfile"; then
            aastex_out=$(python3 "$AASTEX_VALIDATOR" --check "$texfile" 2>&1) || true
            aastex_errors=$(echo "$aastex_out" | grep -c '\[ERROR\]' || true)
            if [[ "$aastex_errors" -gt 0 ]]; then
                echo "$aastex_out"
                echo "    ${YELLOW}[WARN]${NC} AASTeX: $aastex_errors error(s) require manual fix"
                ((violations += aastex_errors))
            else
                echo "    ${GREEN}[OK]${NC} AASTeX validation passed"
            fi
        fi
    fi

    return $violations
}

# --- Main ---
if $HAS_AASTEX; then
    echo "latex-standardizer (General LaTeX Rules + AASTeX v7 Rules)"
else
    echo "latex-standardizer (General LaTeX Rules)"
fi
echo "====================================================="

total_violations=0
for f in "${FILES[@]}"; do
    violations=0
    process_file "$f" || violations=$?
    total_violations=$((total_violations + violations))
done

echo "-----------------------------------------------------"
if $CHECK_MODE; then
    if [[ $total_violations -gt 0 ]]; then
        echo "${RED}Found $total_violations violation(s).${NC}"
        echo "Run with --in-place to auto-fix."
        exit 1
    else
        echo "${GREEN}All checks passed.${NC}"
    fi
else
    echo "${GREEN}Formatting complete for ${#FILES[@]} file(s).${NC}"
fi

exit 0
