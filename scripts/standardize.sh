#!/usr/bin/env bash
# ============================================================================
# latex-standardizer: Best-effort LaTeX .tex source formatting
#
# Pipeline (per file):
#   1. Post-processing (best-effort: sentence splitting, blank lines,
#      preamble grouping)
#   2. latexindent (deterministic: indent, whitespace, environment alignment)
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

# Colors for output
RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
NC=$'\033[0m' # No Color

CHECK_MODE=false
IN_PLACE=false
FILES=()

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

# --- Core function: format one file (PP → latexindent, single pass) ---
run_pipeline() {
    local texfile="$1"
    python3 "$POST_PROCESSOR" --in-place "$texfile" "$CONFIG_YAML" || return 1
    latexindent -l="$CONFIG_YAML" -s -w "$texfile" 2>/dev/null || true
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
        rm -f "$tmpfile"
    elif $IN_PLACE; then
        run_pipeline "$texfile" || {
            echo "    ${RED}[FAIL]${NC} Pipeline failed"
            return 1
        }
        echo "    ${GREEN}[OK]${NC} Formatting applied (PP→latexindent)"
    fi

    return $violations
}

# --- Main ---
echo "latex-standardizer (General LaTeX Rules)"
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
