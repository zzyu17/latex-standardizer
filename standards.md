# LaTeX Source Formatting Standards

General formatting rules for `.tex` source files.

## 1. Indentation

- Use **2 spaces** per indentation level. Never use tabs.
- Indent content inside every `\begin{...}...\end{...}` environment.
- Do not indent the preamble (before `\begin{document}`).
- Do not indent content inside `verbatim`, `lstlisting`, `tabular`,
  or `deluxetable` environments.

```tex
\begin{itemize}
  \item First item
  \item Second item
\end{itemize}
```

## 2. Line Width

- Maximum **80 characters** per line.
- Text lines that exceed 80 chars should be wrapped at sentence boundaries.
- Wrapping does not affect compiled output — LaTeX merges consecutive lines
  into a single paragraph.

## 3. One Sentence Per Line

- Start each sentence on a new line in the source.
- A blank line separates paragraphs.

```tex
This is the first sentence.
This is the second sentence, which compiles into the same paragraph.

This is a new paragraph, separated by a blank line above.
```

- Known abbreviations ending in `.` (e.g., `e.g.`, `i.e.`, `Fig.`) are
  whitelisted and do not trigger sentence splitting. The whitelist is
  defined in `references/latex-standardizer.yaml`.

## 4. Blank Lines Before Semantic Blocks

Insert one blank line before:
- Sectioning commands: `\section`, `\subsection`, `\subsubsection`,
  `\paragraph`, `\subparagraph`
- Block environments: `\begin{itemize}`, `\begin{enumerate}`,
  `\begin{equation}`, `\begin{align}`, `\begin{figure}`,
  `\begin{table}`, `\begin{deluxetable}`, `\begin{verbatim}`,
  `\begin{center}`, and their `*`-starred variants

## 5. Preamble Organization

- Group `\usepackage{}` statements together.
- Sort packages alphabetically within the group.
- Place `\newcommand{}` / `\renewcommand{}` definitions in a separate block
  after the packages block.
- Add a blank line between the packages block and the commands block.

## 6. Whitespace

- No trailing whitespace at end of lines.
- No consecutive blank lines (collapse to a single blank line).
- One blank line before each `\end{...}` that closes a multi-line environment
  (for readability).

## 7. File Structure

```tex
\documentclass[options]{class}

% Packages
\usepackage{...}

% Custom commands
\newcommand{\...}{...}

\begin{document}

\section{...}
...

\end{document}
```

## 8. Encoding

- UTF-8 encoding. No BOM.

## 9. Comments

- Use `%` for comments.
- Align trailing comments where practical.

## References

- LaTeX3 kernel style guide: `l3styleguide.pdf`
- latexindent default configuration: <https://ctan.org/pkg/latexindent>
- TeX StackExchange: ["What are good practices for writing LaTeX code?"](https://tex.stackexchange.com/questions/40788)
