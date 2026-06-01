import re
import tkinter as tk
# ============================================================================
# MARKDOWN RENDERER
# ============================================================================

# Keywords for syntax highlighting (covers Python, JS, TS, C, C++, Java, SQL, Rust, Go)
_KEYWORDS = {
    "def", "class", "import", "from", "if", "elif", "else", "for", "while",
    "return", "try", "except", "finally", "with", "as", "yield", "lambda",
    "pass", "break", "continue", "and", "or", "not", "in", "is", "None",
    "True", "False", "raise", "async", "await", "del", "global", "nonlocal",
    "function", "const", "let", "var", "new", "this", "typeof", "instanceof",
    "throw", "catch", "switch", "case", "default", "export", "extends",
    "implements", "interface", "enum", "type", "void",
    "int", "float", "double", "char", "bool", "string", "long", "short",
    "unsigned", "signed", "struct", "union", "typedef", "sizeof", "static",
    "extern", "inline", "virtual", "override", "public", "private", "protected",
    "abstract", "final", "package", "include", "define", "ifdef", "endif",
    "namespace", "using", "template", "typename",
    "SELECT", "FROM", "WHERE", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP",
    "ALTER", "TABLE", "INDEX", "JOIN", "LEFT", "RIGHT", "INNER", "OUTER",
    "ON", "NULL", "INTO", "VALUES", "SET", "ORDER", "BY", "GROUP",
    "HAVING", "LIMIT", "OFFSET", "DISTINCT", "COUNT", "SUM", "AVG", "MAX",
    "MIN", "LIKE", "BETWEEN", "EXISTS",
    "fn", "mut", "pub", "mod", "use", "crate", "impl", "trait",
    "match", "loop", "move", "ref", "self", "Self", "super", "where",
    "func", "go", "defer", "chan", "select", "range", "map", "make",
    "null", "undefined", "true", "false", "nil",
    "print", "println", "printf", "require", "module", "exports",
}

_KEYWORD_PATTERN = re.compile(
    r'\b(' + '|'.join(re.escape(kw) for kw in sorted(_KEYWORDS, key=len, reverse=True)) + r')\b'
)

INLINE_RE = re.compile(r'(`[^`]+`|\*\*[^*]+?\*\*|\*[^*]+?\*)')


def configure_markdown_tags(widget, colors):
    """Configure text widget tags for markdown rendering."""
    c = colors

    # Headings
    widget.tag_config("md_h1", foreground=c["heading_fg"],
                      font=("Courier New", 14, "bold"), spacing1=8, spacing3=4)
    widget.tag_config("md_h2", foreground=c["heading_fg"],
                      font=("Courier New", 12, "bold"), spacing1=6, spacing3=3)
    widget.tag_config("md_h3", foreground=c["heading_fg"],
                      font=("Courier New", 10, "bold"), spacing1=4, spacing3=2)

    # Inline
    widget.tag_config("md_bold", foreground=c["bold_fg"],
                      font=("Courier New", 9, "bold"))
    widget.tag_config("md_italic", foreground=c["italic_fg"],
                      font=("Courier New", 9, "italic"))
    widget.tag_config("md_inline_code", foreground=c["code_fg"],
                      background=c["code_bg"], font=("Courier New", 9))

    # Code block
    widget.tag_config("code_block", background=c["code_bg"], foreground=c["code_fg"],
                      font=("Courier New", 8), lmargin1=16, lmargin2=16, rmargin=8,
                      spacing1=1, spacing3=1)
    widget.tag_config("code_lang", foreground=c["text_dim"],
                      font=("Courier New", 7, "italic"), lmargin1=16)

    # Syntax highlighting (applied on top of code_block)
    widget.tag_config("code_keyword", foreground=c["code_keyword"])
    widget.tag_config("code_string", foreground=c["code_string"])
    widget.tag_config("code_comment", foreground=c["code_comment"])
    widget.tag_config("code_number", foreground=c["code_number"])

    # Ensure syntax tags override code_block foreground
    for tag_name in ("code_keyword", "code_string", "code_comment", "code_number"):
        widget.tag_raise(tag_name, "code_block")

    # Blockquote
    widget.tag_config("md_blockquote", foreground=c["blockquote_fg"],
                      background=c["blockquote_bg"], font=("Courier New", 9, "italic"),
                      lmargin1=20, lmargin2=20)

    # Lists
    widget.tag_config("md_list", foreground=c["text_normal"],
                      font=("Courier New", 9), lmargin1=20, lmargin2=30)

    # Table
    widget.tag_config("md_table", foreground=c["text_normal"],
                      font=("Courier New", 8), background=c["code_bg"],
                      lmargin1=8, lmargin2=8)
    widget.tag_config("md_table_header", foreground=c["heading_fg"],
                      font=("Courier New", 8, "bold"),
                      background=c["table_header_bg"], lmargin1=8, lmargin2=8)

    # Horizontal rule
    widget.tag_config("md_hr", foreground=c["border"],
                      font=("Courier New", 7), spacing1=4, spacing3=4)

    # Link
    widget.tag_config("md_link", foreground=c["link_fg"],
                      font=("Courier New", 9, "underline"))


def render_markdown(widget, text, colors):
    """Parse markdown text and insert into a tkinter Text widget with formatting."""
    lines = text.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Fenced code block
        if stripped.startswith("```"):
            lang = stripped[3:].strip()
            code_lines = []
            i += 1
            while i < len(lines):
                if lines[i].strip() == "```" or lines[i].strip().startswith("```") and len(lines[i].strip()) == 3:
                    break
                code_lines.append(lines[i])
                i += 1
            if i < len(lines):
                i += 1  # skip closing ```
            _render_code_block(widget, "\n".join(code_lines), lang)
            continue

        # Heading
        if stripped.startswith("### "):
            widget.insert(tk.END, stripped[4:] + "\n", "md_h3")
        elif stripped.startswith("## "):
            widget.insert(tk.END, stripped[3:] + "\n", "md_h2")
        elif stripped.startswith("# "):
            widget.insert(tk.END, stripped[2:] + "\n", "md_h1")

        # Horizontal rule
        elif re.match(r'^[-*_]{3,}\s*$', stripped):
            widget.insert(tk.END, "─" * 40 + "\n", "md_hr")

        # Blockquote
        elif stripped.startswith("> "):
            widget.insert(tk.END, "  │ ", "md_blockquote")
            _render_inline_text(widget, stripped[2:], "md_blockquote")
            widget.insert(tk.END, "\n")

        # Unordered list
        elif re.match(r'^[\s]*[-*+]\s', line):
            indent = len(line) - len(line.lstrip())
            text_content = re.sub(r'^[\s]*[-*+]\s', '', line)
            prefix = "  " * (indent // 2) + "  • "
            widget.insert(tk.END, prefix, "md_list")
            _render_inline_text(widget, text_content, "md_list")
            widget.insert(tk.END, "\n")

        # Ordered list
        elif re.match(r'^[\s]*\d+\.\s', line):
            match_obj = re.match(r'^[\s]*(\d+)\.\s(.*)$', line)
            if match_obj:
                indent = len(line) - len(line.lstrip())
                num = match_obj.group(1)
                text_content = match_obj.group(2)
                prefix = "  " * (indent // 2) + f"  {num}. "
                widget.insert(tk.END, prefix, "md_list")
                _render_inline_text(widget, text_content, "md_list")
                widget.insert(tk.END, "\n")

        # Table
        elif "|" in stripped and stripped.startswith("|"):
            table_lines = [line]
            i += 1
            while i < len(lines) and "|" in lines[i].strip() and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            _render_table(widget, table_lines)
            continue

        # Empty line
        elif not stripped:
            widget.insert(tk.END, "\n")

        # Normal paragraph
        else:
            _render_inline_text(widget, line, "ai_text")
            widget.insert(tk.END, "\n")

        i += 1


def _render_inline_text(widget, text, base_tag):
    """Render text with inline markdown (bold, italic, code) into the widget."""
    parts = INLINE_RE.split(text)
    for part in parts:
        if not part:
            continue
        if part.startswith("`") and part.endswith("`") and len(part) > 1:
            widget.insert(tk.END, part[1:-1], "md_inline_code")
        elif part.startswith("**") and part.endswith("**") and len(part) > 3:
            widget.insert(tk.END, part[2:-2], "md_bold")
        elif part.startswith("*") and part.endswith("*") and len(part) > 1 and not part.startswith("**"):
            widget.insert(tk.END, part[1:-1], "md_italic")
        else:
            widget.insert(tk.END, part, base_tag)


def _render_code_block(widget, code_text, lang):
    """Render a fenced code block with syntax highlighting."""
    if lang:
        widget.insert(tk.END, f"  {lang}\n", "code_lang")

    # Record start position for syntax highlighting
    start_idx = widget.index(tk.END)

    for code_line in code_text.split("\n"):
        widget.insert(tk.END, f"  {code_line}\n", "code_block")

    end_idx = widget.index(tk.END)

    # Apply syntax highlighting
    _apply_syntax_highlighting(widget, start_idx, end_idx)

    widget.insert(tk.END, "\n")


def _apply_syntax_highlighting(widget, start, end):
    """Apply basic syntax highlighting to a code range."""
    try:
        text = widget.get(start, end)
        if not text.strip():
            return

        # Keywords
        for match in _KEYWORD_PATTERN.finditer(text):
            s, e = match.span()
            widget.tag_add("code_keyword", f"{start}+{s}c", f"{start}+{e}c")

        # Strings (double and single quoted)
        for match in re.finditer(r'("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')', text):
            s, e = match.span()
            widget.tag_add("code_string", f"{start}+{s}c", f"{start}+{e}c")

        # Comments (# or //)
        for match in re.finditer(r'(#[^\n]*|//[^\n]*)', text):
            s, e = match.span()
            widget.tag_add("code_comment", f"{start}+{s}c", f"{start}+{e}c")

        # Numbers
        for match in re.finditer(r'\b(\d+\.?\d*(?:e[+-]?\d+)?)\b', text, re.IGNORECASE):
            s, e = match.span()
            widget.tag_add("code_number", f"{start}+{s}c", f"{start}+{e}c")
    except Exception:
        pass  # Syntax highlighting is non-critical


def _render_table(widget, table_lines):
    """Render a markdown table as monospace-aligned text."""
    rows = []
    has_separator = False
    for line in table_lines:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if all(re.match(r'^[-:]+$', c.strip()) for c in cells if c.strip()):
            has_separator = True
            continue
        rows.append(cells)

    if not rows:
        return

    max_cols = max(len(r) for r in rows)
    col_widths = [0] * max_cols
    for row in rows:
        for j, cell in enumerate(row):
            if j < max_cols:
                col_widths[j] = max(col_widths[j], len(cell))

    for idx, row in enumerate(rows):
        tag = "md_table_header" if idx == 0 and has_separator else "md_table"
        line_parts = []
        for j in range(max_cols):
            cell = row[j] if j < len(row) else ""
            line_parts.append(cell.ljust(col_widths[j]))
        widget.insert(tk.END, "  │ " + " │ ".join(line_parts) + " │\n", tag)

        if idx == 0 and has_separator:
            sep_parts = ["─" * w for w in col_widths]
            widget.insert(tk.END, "  ├─" + "─┼─".join(sep_parts) + "─┤\n", "md_table")

    widget.insert(tk.END, "\n")


