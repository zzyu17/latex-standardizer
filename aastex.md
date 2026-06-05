# AASTeX v7 Formatting Standards

AASTeX v7 specific formatting rules for `.tex` source files using
`\documentclass{aastex7...}` (e.g., `aastex701`, `aastex7`).
These rules apply only to AASTeX v7+ and supplement the general
LaTeX standards in `standards.md`.

## 1. Deprecated Commands (Hard Errors)

The following commands have been **removed** from AASTeX v7 and will cause
compilation errors. The script auto-converts where safe, flags where not.

| Deprecated | Replacement | Auto-fix |
|-----------|-------------|----------|
| `\affil{...}` | `\affiliation{...}` | Auto-rename |
| `\acknowledgment{...}` | `\begin{acknowledgments}...\end{acknowledgments}` | Auto-convert |
| `\altaffilmark{...}` | Use `\altaffiliation{...}` | Auto-rename |
| `\altaffiltext{...}` | `\altaffiliation{...}` | Auto-rename |
| `\and` inside `\author{}` | Separate `\author{}` per author | Auto-split |
| `\fullcollaborationName` | Removed, no replacement | Flag only |
| `\deleted{text}` | Remove text entirely | Flag only |
| `\replaced{old}{new}` | `\added{new}` | Flag only |
| `\authorcomment*{...}` | Removed | Flag only |
| `\edit*{...}` | Removed | Flag only |
| `\listofchanges` | Removed | Flag only |
| `rnaas` class option | Removed | Auto-remove |

## 2. Forbidden Packages (Hard Errors)

AASTeX v7 will **error** if these packages are loaded:

- `\usepackage{cite}` — conflicts with `natbib`, which AASTeX uses for bibliography management
- `\usepackage{mcite}` — same as above
- `\usepackage{multicol}` — conflicts with AASTeX layout

The script flags these for removal.

## 3. Structural Validation (Warnings)

The following are **recommended** by AASTeX. The script issues warnings, not errors:

- **`\email{}` per author block** — Each `\author{}` should be followed by
  at least one `\email{}`. Missing emails cause compiler warnings in v7.
- **`\correspondingauthor{...}`** — Recommended but not required.
- **`\bibliographystyle{aasjournalv7}`** — Prefer the v7 BST file
  distributed with AASTeX, but other BST files may be valid for specific journals.
- **`\keywords{...}` separator** — AAS convention uses `---` (em-dash)
  as separator. Commas are discouraged. Auto-conversion is best-effort.

## 4. ORCID Format Validation

If an ORCID is present in `\author[ORCID]{...}`, it must match the format
`0000-0000-0000-0000` (16 digits with hyphens). ORCID is **optional**,
the script validates format only when present.

## 5. Manual Review by LLM

These rules require semantic judgment — the script detects and reports them,
but the LLM must decide the fix:

| Rule | Why Manual |
|------|-----------|
| `tabular` → `deluxetable` conversion | Requires understanding table structure |
| `\deleted{text}` → removal decision | Must verify text should be removed |
| `\replaced{old}{new}` → `\added{new}` | Must verify semantic correctness |
| Title-case in `\title{}` | Natural language understanding |
| `\uat{}` UAT concept-ID selection | Astronomy domain knowledge |
| Author-to-affiliation pairing | Requires semantic grouping |
| `\collaboration{number}` correctness | Depends on author list structure |
| Figure `\plotone` vs `\plottwo` choice | Visual layout judgment |

## Version Scope

These rules target **AASTeX v7+** only (`\documentclass{aastex7...}`).
AASTeX v6.x files (e.g., `aastex63`, `aastex631`) are **not** detected
and will not trigger AASTeX validation — only general LaTeX rules apply.

## References

- AASTeX 7.0.1 class file: `aastex701.cls`
- AAS Journals v7 author guide: <https://journals.aas.org/aastexguide/>
- v7 revision history (distributed with AASTeX)
