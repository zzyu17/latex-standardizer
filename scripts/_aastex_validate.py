#!/usr/bin/env python3
"""
AASTeX v7 validator for latex-standardizer.

Checks .tex files for compliance with AASTeX v7 specific rules.
Only invoked for files using \\documentclass{aastex7...}.
--check: reports violations only
--in-place: applies safe auto-fixes, then reports remaining violations

Severity levels:
  ERROR   (red)    — Will cause LaTeX compilation failure
  WARNING (yellow) — Recommended but not strictly enforced
  MANUAL  (cyan)   — Requires human/LLM judgment to fix
"""
import sys
import re
import os
from collections import OrderedDict

# --- Color helpers ---
RED = '\033[0;31m'
YELLOW = '\033[0;33m'
CYAN = '\033[0;36m'
BOLD = '\033[1m'
RESET = '\033[0m'

def red(text):    return f"{RED}{text}{RESET}"
def yellow(text): return f"{YELLOW}{text}{RESET}"
def cyan(text):   return f"{CYAN}{text}{RESET}"
def bold(text):   return f"{BOLD}{text}{RESET}"


def read_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def find_author_blocks(text):
    """Find author blocks: lines from \\author through next \\email or \\affiliation
    ending. Returns list of (start_line, end_line, block_text)."""
    lines = text.split('\n')
    blocks = []
    in_block = False
    block_start = None

    for i, line in enumerate(lines):
        stripped = line.lstrip()
        # Remove trailing comments for matching
        code = stripped.split('%')[0].strip() if '%' in stripped else stripped

        if code.startswith('\\author'):
            in_block = True
            block_start = i
        elif in_block:
            if (code.startswith('\\email') or
                    code.startswith('\\affiliation') or
                    code.startswith('\\altaffiliation') or
                    code.startswith('\\collaboration') or
                    code.startswith('\\nocollaboration')):
                continue  # still in block
            # Check if next author starts
            if code.startswith('\\author'):
                blocks.append((block_start, i - 1, lines[block_start:i]))
                block_start = i
            elif (code.startswith('\\begin{abstract}') or
                  code.startswith('\\title') or
                  code.startswith('\\correspondingauthor') or
                  code.startswith('\\keywords') or
                  (code == '' and i + 1 < len(lines) and
                   lines[i + 1].lstrip().startswith('\\begin{abstract}'))):
                blocks.append((block_start, i - 1, lines[block_start:i]))
                in_block = False

    if in_block:
        blocks.append((block_start, len(lines) - 1, lines[block_start:]))

    return blocks


class Violation:
    def __init__(self, line_no, severity, message, fix=None):
        self.line_no = line_no
        self.severity = severity  # 'error', 'warning', 'manual'
        self.message = message
        self.fix = fix  # optional: (old_text, new_text) for auto-fix

    def format(self):
        color_fn = {'error': red, 'warning': yellow, 'manual': cyan}
        c = color_fn.get(self.severity, str)
        prefix = c(f"[{self.severity.upper()}]")
        loc = f"L{self.line_no}" if self.line_no else ""
        return f"  {prefix} {loc} {self.message}"

    def __repr__(self):
        return f"Violation(L{self.line_no}, {self.severity}, {self.message[:40]}...)"


# --- Check functions ---

DEPRECATED_SIMPLE = {
    # (pattern, replacement, severity)
    # Safe auto-renames (same syntax, just rename the command)
    (r'\\affil\b', r'\\affiliation', 'error'):
        r'Found \affil — use \affiliation instead',
    (r'\\altaffilmark\b', r'\\altaffiliation', 'warning'):
        r'Found \altaffilmark — use \altaffiliation instead',
    (r'\\altaffiltext\b', r'\\altaffiliation', 'warning'):
        r'Found \altaffiltext — use \altaffiliation instead',
}

DEPRECATED_FLAG_ONLY = {
    # (pattern, message, severity)
    r'\\fullcollaborationName':
        (r'Found \fullcollaborationName — removed in AASTeX v7, no replacement', 'manual'),
    r'\\deleted\{':
        (r'Found \deleted{{}} — removed in AASTeX v7 (trackchanges option removed it); remove the text or migrate', 'manual'),
    r'\\replaced\{':
        (r'Found \replaced{{}} — removed in AASTeX v7; use \added{{new}} only', 'manual'),
    r'\\authorcomment\*\{':
        (r'Found \authorcomment* — removed in AASTeX v7', 'manual'),
    r'\\edit\*\{':
        (r'Found \edit* — removed in AASTeX v7', 'manual'),
    r'\\listofchanges':
        (r'Found \listofchanges — removed in AASTeX v7', 'manual'),
    r'\\acknowledgment\b(?!s\b)':
        (r'Found \acknowledgment (deprecated) — must be converted to \begin{acknowledgments}...\end{acknowledgments} environment (manual: structural change)', 'error'),
}


def check_deprecated_simple(text):
    """Check for deprecated commands with safe auto-renames."""
    violations = []
    lines = text.split('\n')
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith('%'):
            continue
        for (pattern, replacement, severity), msg in DEPRECATED_SIMPLE.items():
            if re.search(pattern, stripped):
                violations.append(Violation(
                    i + 1, severity, msg,
                    fix=(pattern, replacement)
                ))
    return violations


def check_deprecated_flag_only(text):
    """Check for deprecated commands that require manual review."""
    violations = []
    lines = text.split('\n')
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith('%'):
            continue
        for pattern, (msg, severity) in DEPRECATED_FLAG_ONLY.items():
            if re.search(pattern, stripped):
                violations.append(Violation(i + 1, severity, msg))
    return violations


def check_and_in_author(text):
    """Check for \\and inside \\author{} — must split into separate authors."""
    violations = []
    lines = text.split('\n')
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith('%'):
            continue
        if re.search(r'\\author\[?.*\]?\{.*\\and\s', stripped):
            violations.append(Violation(
                i + 1, 'warning',
                r'Found \and inside \author{} — AASTeX v7 does not support \and; split into separate \author{} commands'
            ))
    return violations


FORBIDDEN_PACKAGES = {
    'cite': 'AASTeX v7 uses natbib; loading cite causes errors',
    'mcite': 'mcite conflicts with AASTeX natbib handling',
    'multicol': 'multicol conflicts with AASTeX column layout',
}


def check_forbidden_packages(text):
    """Check for forbidden \\usepackage{} calls."""
    violations = []
    lines = text.split('\n')
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith('%'):
            continue
        m = re.match(r'\\usepackage(?:\[.*?\])?\{(.*?)\}', stripped)
        if m:
            pkgs = [p.strip() for p in m.group(1).split(',')]
            for pkg in pkgs:
                if pkg in FORBIDDEN_PACKAGES:
                    violations.append(Violation(
                        i + 1, 'error',
                        f'Forbidden package: \\usepackage{{{pkg}}} — {FORBIDDEN_PACKAGES[pkg]}'
                    ))
    return violations


def check_rnaas_option(text):
    """Check for deprecated 'rnaas' class option."""
    violations = []
    lines = text.split('\n')
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith('%'):
            continue
        m = re.match(r'\\documentclass(?:\[.*?\])?\{(.*?)\}', stripped)
        if m:
            # Check for rnaas in options
            opts_match = re.match(r'\\documentclass\[(.*?)\]\{', stripped)
            if opts_match:
                opts = [o.strip() for o in opts_match.group(1).split(',')]
                if 'rnaas' in opts:
                    violations.append(Violation(
                        i + 1, 'error',
                        r'Class option "rnaas" was removed in AASTeX v7 — remove from \documentclass'
                    ))
    return violations


def check_email_per_author(text):
    """Check that each \\author{} has an \\email{} following it."""
    violations = []
    blocks = find_author_blocks(text)
    for start, end, block_lines in blocks:
        block_text = '\n'.join(block_lines)
        has_email = bool(re.search(r'\\email', block_text))
        if not has_email:
            # Find the author line
            for j, bl in enumerate(block_lines):
                if re.search(r'\\author', bl):
                    violations.append(Violation(
                        start + j + 1, 'warning',
                        r'Author block missing \email{} — AASTeX v7 requires \email per author'
                    ))
                    break
    return violations


def check_corresponding_author(text):
    """Check for \\correspondingauthor{} presence."""
    violations = []
    if not re.search(r'\\correspondingauthor\{', text):
        violations.append(Violation(
            None, 'warning',
            r'No \correspondingauthor{} found — recommended for AASTeX v7 submissions'
        ))
    return violations


def check_bibliographystyle(text):
    """Check \\bibliographystyle is aasjournalv7 (or similar)."""
    violations = []
    lines = text.split('\n')
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith('%'):
            continue
        m = re.match(r'\\bibliographystyle\{(.*?)\}', stripped)
        if m:
            bst = m.group(1).strip()
            if not bst.startswith('aasjournal'):
                violations.append(Violation(
                    i + 1, 'warning',
                    f'\\bibliographystyle{{{bst}}} — AASTeX v7 recommends aasjournalv7.bst'
                ))
    return violations


def check_keywords_separator(text):
    """Check that \\keywords{} uses --- (em-dash) not commas as separator."""
    violations = []
    lines = text.split('\n')
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith('%'):
            continue
        m = re.match(r'\\keywords\{(.*?)\}\s*$', stripped)
        if m:
            content = m.group(1)
            # Check for comma-separated (non-UAT) keywords
            # UAT format: \uat{Label}{ID} --- \uat{Label}{ID}
            # If there are commas between keyword items, flag
            # Remove \uat{...} blocks for checking
            without_uat = re.sub(r'\\uat\{[^}]*\}\{[^}]*\}', '<<UAT>>', content)
            # Check if commas appear between items (not inside braces)
            if re.search(r',\s*\S', without_uat):
                violations.append(Violation(
                    i + 1, 'warning',
                    r'\keywords{} may use commas — AASTeX convention is " --- " (em-dash) between keywords'
                ))
    return violations


def check_orcid_format(text):
    """Validate ORCID format when present. ORCID is optional."""
    violations = []
    lines = text.split('\n')
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith('%'):
            continue
        m = re.match(r'\\author\[(.*?)\]', stripped)
        if m:
            opt = m.group(1)
            # Parse key=value pairs or direct ORCID
            if '=' in opt:
                # key=value format
                orcid_match = re.search(r'orcid=([\d\-]+)', opt)
                if orcid_match:
                    orcid_val = orcid_match.group(1)
                    if not re.match(r'^\d{4}-\d{4}-\d{4}-\d{4}$', orcid_val):
                        violations.append(Violation(
                            i + 1, 'manual',
                            f'ORCID format may be invalid: {orcid_val} — should be 0000-0000-0000-0000'
                        ))
            elif opt.strip():
                # Direct ORCID value
                if not re.match(r'^\d{4}-\d{4}-\d{4}-\d{4}$', opt.strip()):
                    violations.append(Violation(
                        i + 1, 'manual',
                        f'ORCID format may be invalid: {opt} — should be 0000-0000-0000-0000'
                    ))
    return violations


def check_tabular_usage(text):
    """Flag tabular usage suggesting deluxetable instead."""
    violations = []
    lines = text.split('\n')
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith('%'):
            continue
        if re.search(r'\\begin\{tabular\}', stripped):
            # Skip if inside comments
            violations.append(Violation(
                i + 1, 'manual',
                r'Found \begin{tabular} — AASTeX prefers deluxetable for tables. Consider converting if appropriate.'
            ))
    return violations


# --- Main validation ---

ALL_CHECKS = [
    ('deprecated_simple', check_deprecated_simple),
    ('deprecated_flag_only', check_deprecated_flag_only),
    ('and_in_author', check_and_in_author),
    ('forbidden_packages', check_forbidden_packages),
    ('rnaas_option', check_rnaas_option),
    ('email_per_author', check_email_per_author),
    ('corresponding_author', check_corresponding_author),
    ('bibliographystyle', check_bibliographystyle),
    ('keywords_separator', check_keywords_separator),
    ('orcid_format', check_orcid_format),
    ('tabular_usage', check_tabular_usage),
]


def run_checks(text):
    violations = []
    for name, fn in ALL_CHECKS:
        try:
            v = fn(text)
            violations.extend(v)
        except Exception as e:
            print(f"  [SKIP] Check '{name}' failed: {e}", file=sys.stderr)
    return violations


def apply_fix(text, violation):
    """Apply a safe auto-fix. Returns new text."""
    if violation.fix is None:
        return text
    pattern, replacement = violation.fix
    lines = text.split('\n')
    if violation.line_no:
        idx = violation.line_no - 1
        old_line = lines[idx]
        # Only apply fix to code part (before % comment)
        code, sep, comment = old_line.partition('%')
        if sep:
            new_code = re.sub(pattern, replacement, code)
            lines[idx] = new_code + sep + comment
        else:
            lines[idx] = re.sub(pattern, replacement, old_line)
    return '\n'.join(lines)


def process_file(filepath, check_mode=False):
    """Process a single .tex file. check_mode: only report, don't write.
    Returns list of remaining violations after auto-fix (empty if clean)."""
    text = read_file(filepath)
    violations = run_checks(text)

    if check_mode:
        return violations

    # In-place mode: apply safe auto-fixes
    auto_fixable = [v for v in violations if v.fix is not None]
    if auto_fixable:
        for v in auto_fixable:
            text = apply_fix(text, v)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(text)

    # Filter out auto-fixed violations, keep the rest
    remaining = [v for v in violations if v.fix is None]
    return remaining


def main():
    mode = sys.argv[1]
    if mode not in ('--check', '--in-place'):
        print("Usage: _aastex_validate.py [--check|--in-place] <file.tex>", file=sys.stderr)
        sys.exit(2)

    filepath = sys.argv[2]

    if not os.path.exists(filepath):
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    violations = process_file(filepath, check_mode=(mode == '--check'))

    if mode == '--check':
        errors = [v for v in violations if v.severity == 'error']
        for v in violations:
            prefix = {'error': red('[ERROR]'), 'warning': yellow('[WARN]'),
                      'manual': cyan('[MANUAL]')}.get(v.severity, '[FAIL]')
            loc = f"L{v.line_no}: " if v.line_no else ""
            print(f"    {prefix} {loc}{v.message}")
        if errors:
            sys.exit(1)
        sys.exit(0)


if __name__ == '__main__':
    main()
