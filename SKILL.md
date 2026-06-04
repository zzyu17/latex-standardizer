---
name: latex-standardizer
slug: latex-standardizer
version: 1.0.0
description: Format and standardize LaTeX `.tex` source files with configurable rules and git pre-commit integration
---

## When to Use

User asks to format, standardize, or clean up LaTeX `.tex` source files.
Triggers on: "format tex", "standardize latex", "clean up tex file",
"fix latex indentation", "latex style guide", "tex formatting".

## Core Rules

1. **Run the script first.** Always run `scripts/standardize.sh --in-place <file.tex>`
   before any manual edits. The script handles all deterministic and best-effort
   fixes.

2. **Respect the config.** All formatting rules are defined in
   `references/latex-standardizer.yaml`. Read it before making changes — the YAML is
   the single source of truth for: indent rules, sentence-split abbreviations,
   blank-line triggers, and preamble organization.

3. **Two-pass workflow.**
   (a) Phase 1 auto-fix via `scripts/standardize.sh --in-place <file.tex>`;
   (b) Review the output and handle residual issues that the script flagged but
   could not fix: label naming consistency (`sec:`, `fig:`, `tab:`), redundant
   packages, and abbreviation false-positives.

4. **Never alter compiled output.** Only source formatting changes. If a change
   would affect the PDF, it belongs in a separate review pass.

5. **Report before finishing.** Always summarize: violations found → violations
   auto-fixed → violations requiring manual judgment.

6. **Git hook available.** Install `scripts/pre-commit` as `.git/hooks/pre-commit`
   to enforce rules on every commit for `.tex` files.

## Quick Reference

| Topic                          | File                                 |
|--------------------------------|--------------------------------------|
| General LaTeX formatting rules | `standards.md`                       |
| YAML config                    | `references/latex-standardizer.yaml` |
| Main formatting script         | `scripts/standardize.sh`             |
| Post-processing helper         | `scripts/_post_process.py`           |
| Git pre-commit hook            | `scripts/pre-commit`                 |
