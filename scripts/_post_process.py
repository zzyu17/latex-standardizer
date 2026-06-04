#!/usr/bin/env python3
"""
Post-processor for latex-standardizer.
Handles best-effort semantic formatting that latexindent cannot do:
  1. One-sentence-per-line splitting (abbreviation-whitelist-aware)
  2. Blank line insertion before semantic blocks
  3. Long-line wrapping at sentence boundaries
  4. Preamble grouping (packages block → commands block)

Reads configuration from the YAML config file.
"""
import sys
import re
import os

try:
    import yaml
except ImportError:
    print("Error: PyYAML is required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


def load_config(config_path):
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def load_abbreviation_whitelist(config):
    """Extract abbreviation whitelist from config, return as a set."""
    try:
        abbrs = config['sentence_split']['abbreviation_whitelist']
        return set(abbrs)
    except (KeyError, TypeError):
        return set()


def load_blank_line_triggers(config):
    """Extract blank-line-before triggers from config."""
    triggers = set()
    try:
        blb = config['blank_line_before']
        for lst in blb.values():
            if isinstance(lst, list):
                triggers.update(lst)
    except (KeyError, TypeError):
        pass
    return triggers


def load_line_wrap_config(config):
    """Extract line-wrapping settings."""
    try:
        lw = config['line_wrap']
        return {
            'max_chars': lw.get('max_chars', 80),
            'split_at_sentence': lw.get('split_at_sentence', True),
        }
    except (KeyError, TypeError):
        return {'max_chars': 80, 'split_at_sentence': True}


def load_preamble_config(config):
    """Extract preamble organization settings."""
    try:
        return config.get('preamble', {})
    except (KeyError, TypeError):
        return {}


# --- Sentence splitting ---

def is_abbreviation(word, whitelist):
    """Check if a word ending with '.' is a known abbreviation."""
    return word in whitelist


def split_sentences(line, whitelist):
    """
    Split a line into sentences at '. ', '! ', '? ' boundaries,
    respecting the abbreviation whitelist.
    Returns list of sentence strings.
    """
    if not line.strip():
        return [line]

    sentences = []
    current = ""
    i = 0
    chars = list(line)
    n = len(chars)

    while i < n:
        current += chars[i]
        # Check for sentence-ending punctuation followed by space
        if (chars[i] in '.!?' and
                i + 1 < n and chars[i + 1] == ' '):
            # Extract the word that ends with punctuation
            # Walk back to find the word start
            j = len(current) - 1
            while j > 0 and current[j - 1] not in ' \t\n':
                j -= 1
            word_candidate = current[j:].strip()

            if word_candidate in whitelist:
                # Known abbreviation — don't split
                i += 1
                continue
            elif re.match(r'^[A-Z]$', word_candidate[:-1]):
                # Single capital letter followed by '.' (e.g., "A.") — abbreviation
                i += 1
                continue
            elif re.match(r'^\d+\.$', word_candidate):
                # Number followed by '.' (e.g., "1.") — don't split
                i += 1
                continue
            else:
                # Genuine sentence end
                sentences.append(current.rstrip())
                current = ""
                i += 1  # skip the space after punctuation
        i += 1

    if current.strip():
        sentences.append(current)

    return sentences if sentences else [line]


# --- Blank line insertion ---

def get_blank_line_triggers_from_text(config):
    """Build regex pattern and plain-text triggers for blank-line insertion."""
    triggers = load_blank_line_triggers(config)
    return sorted(triggers, key=len, reverse=True)  # longest first to avoid partial matches


def insert_blank_lines(lines, triggers):
    """Insert a blank line before lines that match any trigger."""
    result = []
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        for trigger in triggers:
            if stripped.startswith(trigger):
                # Only insert blank line if the previous line is not already blank
                if result and result[-1].strip() != '':
                    result.append('')
                break
        result.append(line)
    return result


# --- Line wrapping ---

def wrap_long_lines(lines, max_chars):
    """Wrap lines exceeding max_chars at sentence boundaries.
    All wrapped lines are output without leading whitespace so latexindent
    owns indentation completely.
    Uses max_chars - 2 internally as effective limit to account for the
    2-space indent that latexindent will add, ensuring idempotency."""
    effective_max = max_chars - 2  # buffer for latexindent's indent
    min_tail = 15  # don't leave a trailing chunk shorter than this
    result = []
    for line in lines:
        stripped = line.lstrip()
        if len(stripped) <= effective_max:
            result.append(stripped)
            continue
        # Try to break at the last sentence boundary within effective_max
        wrapped = []
        remaining = stripped
        while len(remaining) > effective_max:
            # Find the best split position within effective_max
            split_pos = _find_split_pos(remaining, effective_max)
            # Don't split if it would leave a tiny tail
            tail = remaining[split_pos:].lstrip()
            if len(tail) <= min_tail:
                # Keep the tail with the previous chunk even if it exceeds limit
                wrapped.append(remaining.rstrip())
                remaining = ''
                break
            wrapped.append(remaining[:split_pos].rstrip())
            remaining = remaining[split_pos:].lstrip()
        if remaining:
            wrapped.append(remaining)
        result.extend(wrapped)
    return result


def _find_split_pos(text, limit):
    """Find the best position to split text within limit chars.
    Prefers sentence boundaries ('. ', '! ', '? '), then word boundaries.
    Avoids splitting right before '(' or '[' — backs up to previous word
    boundary so the opening bracket stays with its content."""
    # Try sentence boundary first
    split_pos = limit
    for m in re.finditer(r'[.!?]\s', text[:limit]):
        split_pos = m.end()
    if split_pos < limit:
        return split_pos
    # No sentence boundary — try word boundary, avoiding '(' and '['
    split_pos = limit
    for m in re.finditer(r'\s', text[:limit]):
        candidate = m.start()
        # Check if the character after this space is '(' or '['
        after = text[candidate:].lstrip()
        if after and after[0] in '([':
            continue  # don't split before an opening bracket
        split_pos = candidate
    return split_pos


# --- Preamble grouping ---

def is_package_line(line):
    """Check if a line is a \\usepackage command."""
    stripped = line.strip()
    return stripped.startswith('\\usepackage')


def is_command_def_line(line):
    """Check if a line is a command/environment definition."""
    stripped = line.strip()
    return (stripped.startswith('\\newcommand') or
            stripped.startswith('\\renewcommand') or
            stripped.startswith('\\newenvironment') or
            stripped.startswith('\\renewenvironment') or
            stripped.startswith('\\def') or
            stripped.startswith('\\let') or
            stripped.startswith('\\newtheorem'))


# --- Preamble grouping ---

def group_preamble(lines, config):
    """Group \\usepackage and \\newcommand blocks in preamble.
    Purely structural: no marker comments are inserted."""
    preamble_ops = config
    if not preamble_ops.get('group_packages', True):
        return lines

    before_doc = []
    after_doc = []
    in_body = False

    for line in lines:
        if line.strip() == '\\begin{document}':
            in_body = True
        if in_body:
            after_doc.append(line)
        else:
            before_doc.append(line)

    if not before_doc:
        return lines

    # Classify preamble lines
    packages = []
    commands = []
    other = []

    for line in before_doc:
        if is_package_line(line):
            packages.append(line)
        elif is_command_def_line(line):
            commands.append(line)
        else:
            other.append(line)

    # Sort packages if requested
    if preamble_ops.get('sort_packages', True) and packages:
        packages.sort(key=lambda x: x.strip().lower())

    # Rebuild preamble
    result = list(other)
    # Remove trailing blank lines before adding blocks
    while result and result[-1].strip() == '':
        result.pop()

    if packages:
        if result and result[-1].strip() != '':
            result.append('')
        result.extend(packages)

    if commands:
        if result and result[-1].strip() != '':
            result.append('')
        result.extend(commands)

    return result + after_doc


# --- Orphaned fragment rejoining ---

def rejoin_orphans(lines):
    """Rejoin sentence fragments that were split by original line breaks.

    Sentence splitting on ". " can produce orphaned line fragments when the
    original had a manual line break between "word." and "Next..." on separate
    lines. A fragment should be rejoined if:
      (a) It is a single capitalized word like "At", "The" — the original
          line-end fell right after a sentence boundary.
      (b) The next line starts with lowercase — current line was split
          mid-sentence by a line break in the original.

    Runs greedily (don't advance after join) to handle multi-hop rejoins.
    """
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        if not stripped or stripped.startswith('%') or stripped.startswith('\\'):
            i += 1
            continue
        if i + 1 >= len(lines):
            break
        next_line = lines[i + 1]
        next_stripped = next_line.lstrip()
        if not next_stripped or next_stripped.startswith('%') or next_stripped.startswith('\\'):
            i += 1
            continue
        is_single_word = len(stripped.split()) == 1 and stripped[0].isupper()
        is_lowercase_continuation = next_stripped and next_stripped[0].islower()
        if is_single_word or is_lowercase_continuation:
            lines[i] = line.rstrip() + ' ' + next_line.lstrip()
            lines.pop(i + 1)
        else:
            i += 1
    return lines


def join_dangling_brackets(lines):
    """Join lines ending with '(' or '[' to the next line.

    Runs as a separate step so the merged line is then handled by
    wrap_long_lines if it exceeds the line limit. Unlike rejoin_orphans,
    this does not skip next lines starting with \\ — a '(' at end of
    a text line should join with the \\texttt or similar that follows.
    """
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        if not stripped or stripped.startswith('%'):
            i += 1
            continue
        if i + 1 >= len(lines):
            break
        next_line = lines[i + 1]
        next_stripped = next_line.lstrip()
        if not next_stripped or next_stripped.startswith('%'):
            i += 1
            continue
        if stripped.endswith('(') or stripped.endswith('['):
            lines[i] = line.rstrip() + ' ' + next_line.lstrip()
            lines.pop(i + 1)
        else:
            i += 1
    return lines


def process_file(filepath, config, check_mode=False):
    """Process a single .tex file. Returns list of violations if check_mode."""
    with open(filepath, 'r', encoding='utf-8') as f:
        original_lines = [line.rstrip('\n') for line in f]

    whitelist = load_abbreviation_whitelist(config)
    triggers = get_blank_line_triggers_from_text(config)
    wrap_cfg = load_line_wrap_config(config)
    preamble_cfg = load_preamble_config(config)

    lines = list(original_lines)
    violations = []

    # --- Step 1: One-sentence-per-line ---
    # Strip leading whitespace from sentence lines so latexindent owns all
    # indentation. This makes the PP idempotent and guarantees single-pass
    # convergence: PP normalizes text, latexindent re-indents.
    if config.get('sentence_split', {}).get('enabled', True):
        new_lines = []
        for line in lines:
            stripped = line.strip()
            # Skip lines that are commands, environments, comments, empty
            if (not stripped or
                    stripped.startswith('%') or
                    stripped.startswith('\\') or
                    stripped.startswith('}') or
                    re.match(r'^\s*$', line)):
                new_lines.append(line)
                continue
            # Split text lines into sentences, stripping leading whitespace
            sentences = split_sentences(line, whitelist)
            for s in sentences:
                new_lines.append(s.lstrip())
        lines = new_lines

    # --- Step 2: Blank line insertion ---
    lines = insert_blank_lines(lines, triggers)

    # --- Step 3: Rejoin orphaned sentence fragments ---
    # Must run BEFORE line wrapping so the complete sentence length is known.
    lines = rejoin_orphans(lines)

    # --- Step 3.5: Join dangling brackets ---
    lines = join_dangling_brackets(lines)

    # --- Step 4: Line wrapping ---
    max_chars = wrap_cfg.get('max_chars', 80)
    lines = wrap_long_lines(lines, max_chars)

    # --- Step 5: Preamble grouping ---
    lines = group_preamble(lines, preamble_cfg)

    # --- Step 6: Collapse multiple blank lines ---
    result = []
    prev_blank = False
    for line in lines:
        is_blank = line.strip() == ''
        if is_blank and prev_blank:
            continue
        result.append(line)
        prev_blank = is_blank
    # Remove trailing blank lines
    while result and result[-1].strip() == '':
        result.pop()
    # Ensure file ends with newline by adding a blank line back
    result.append('')

    # --- Compare ---
    original_text = '\n'.join(original_lines) + '\n'
    result_text = '\n'.join(result) + '\n'

    if original_text != result_text:
        if check_mode:
            # Generate diff summary
            violations.append("Post-processing would modify this file")
        else:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(result_text)

    return violations


def main():
    mode = sys.argv[1]
    if mode not in ('--check', '--in-place'):
        print("Usage: _post_process.py [--check|--in-place] <file.tex> <config.yaml>", file=sys.stderr)
        sys.exit(2)

    filepath = sys.argv[2]
    config_path = sys.argv[3]

    if not os.path.exists(filepath):
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    config = load_config(config_path)
    violations = process_file(filepath, config, check_mode=(mode == '--check'))

    if mode == '--check':
        for v in violations:
            print(f"    [FAIL] {v}")
        if violations:
            sys.exit(1)
        else:
            sys.exit(0)


if __name__ == '__main__':
    main()
