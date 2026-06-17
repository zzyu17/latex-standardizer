# LaTeX Standardizer

A skill for standardizing LaTeX source (`.tex`) files to match community conventions and journal-specific (currently AASTeX) requirements. It provides a robust, idempotent, single-pass formatting pipeline.

## Branches

This repository is maintained across two branches depending on your project needs:

- **`master`**: Contains the core, general LaTeX formatting rules (semantic sentence splitting, 2-space indentation, max 80 characters line wrapping, preamble grouping, and orphan rejoining). Suitable for any standard LaTeX project.
- **`aastex`**: Builds upon `master` by adding AASTeX v7.0.1 specific validation and auto-fixes (deprecated commands, forbidden packages, structural validation, and ORCID formatting). Ideal for standardizing AAS journal manuscripts.

## Features

- **Semantic Sentence Splitting**: Enforces the one-sentence-per-line rule using abbreviation whitelists to avoid false splits.
- **Deterministic Indentation**: Uses `latexindent` to ensure consistent 2-space environment and command indentation.
- **Smart Line Wrapping**: Wraps long lines up to 80 characters while respecting indentation and LaTeX semantics.
- **Preamble Grouping**: Automatically organizes `\usepackage`, `\newcommand`, and `\newenvironment` declarations into neat, separated blocks.
- **Orphan Rejoining**: Prevents awkward single-word wrapping and dangling brackets.
- **AASTeX v7 Validator** *(on `aastex` branch)*: Automatically flags and fixes deprecated commands, and validates structural integrity against AASTeX guidelines.

## Prerequisites

- **Python 3** with the `PyYAML` package
- **latexindent** (typically included with TeX Live or MiKTeX installations)

## Installation

Clone this repository into your AI assistant's skills/plugins directory:

```bash
cd <skills/plugins-directory>
git clone https://github.com/zzyu17/latex-standardizer.git
```

Checkout the branch you need:

```bash
cd latex-standardizer

# For general LaTeX rules:
git checkout master

# For AASTeX v7 specific rules:
git checkout aastex
```

## Usage

### As an AI Skill
Activate the skill in your chat or CLI session. The assistant will orchestrate the formatting pipeline, apply auto-fixes, and highlight any domain-specific issues that require your manual review.

### Standalone CLI Script
You can directly run the standardization pipeline on your `.tex` files without an AI assistant for auto-fixing and validation:

```bash
scripts/standardize.sh path/to/your/manuscript.tex
```

### Git Pre-commit Hook
To ensure your `.tex` files are always standardized before committing, use the provided pre-commit hook:

```bash
ln -s "$(readlink -f scripts/pre-commit)" .git/hooks/pre-commit
```

Or just activate the skill — the assistant will detect your Git repo, ask whether you want to install the hook and install it via symlink for you if you approve.

## Configuration

The underlying configuration for both `latexindent` and the Python post-processor is located in `references/latex-standardizer.yaml`.
You can customize abbreviation whitelists, blank-line triggers, and line wrapping limits, etc. by editing this file.
