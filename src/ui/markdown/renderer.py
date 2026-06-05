import re
import tkinter as tk
import markdown
from html.parser import HTMLParser
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


def clean_bmp(text):
    """Convert Unicode characters outside BMP (e.g. emojis) to UTF-16 surrogate pairs for Tkinter compatibility on Windows."""
    if not isinstance(text, str):
        return text
    result = []
    for c in text:
        cp = ord(c)
        if cp > 0xffff:
            high = (cp - 0x10000) // 0x400 + 0xD800
            low = (cp - 0x10000) % 0x400 + 0xDC00
            result.append(chr(high) + chr(low))
        else:
            result.append(c)
    return "".join(result)


def safe_insert(widget, index, text, tags=None):
    """Safely insert text into a Tkinter widget, avoiding crashes from non-BMP characters."""
    if tags is not None:
        widget.insert(index, clean_bmp(text), tags)
    else:
        widget.insert(index, clean_bmp(text))


class HTMLToTkinterParser(HTMLParser):
    """Parses generated HTML representation of Markdown and renders it into a Tkinter Text widget."""

    def __init__(self, widget, colors):
        super().__init__()
        self.widget = widget
        self.colors = colors
        self.tag_stack = []
        self.current_tags = []
        self.list_counters = []
        
        # State variables
        self.in_table = False
        self.table_rows = []
        self.current_row = []
        self.in_thead = False
        self.in_code = False
        self.code_text = []
        self.code_lang = ""

    def handle_starttag(self, tag, attrs):
        self.tag_stack.append(tag)
        attrs_dict = dict(attrs)
        
        if tag == 'h1':
            self.current_tags.append('md_h1')
        elif tag == 'h2':
            self.current_tags.append('md_h2')
        elif tag == 'h3':
            self.current_tags.append('md_h3')
        elif tag in ('strong', 'b'):
            self.current_tags.append('md_bold')
        elif tag in ('em', 'i'):
            self.current_tags.append('md_italic')
        elif tag == 'code':
            self.in_code = True
            if 'pre' in self.tag_stack:
                self.current_tags.append('code_block')
                cls = attrs_dict.get('class', '')
                if cls.startswith('language-'):
                    self.code_lang = cls[9:]
            else:
                self.current_tags.append('md_inline_code')
        elif tag == 'blockquote':
            self.current_tags.append('md_blockquote')
            safe_insert(self.widget, tk.END, "  │ ", tuple(self.current_tags))
        elif tag == 'ol':
            self.list_counters.append(1)
        elif tag == 'ul':
            self.list_counters.append(None)
        elif tag == 'li':
            nesting = len(self.list_counters)
            indent = "  " * (nesting - 1)
            if self.list_counters and self.list_counters[-1] is not None:
                num = self.list_counters[-1]
                prefix = f"{indent}{num}. "
                self.list_counters[-1] += 1
            else:
                prefix = f"{indent}• "
            safe_insert(self.widget, tk.END, prefix, 'md_list')
            self.current_tags.append('md_list')
        elif tag == 'table':
            self.in_table = True
            self.table_rows = []
        elif tag == 'thead':
            self.in_thead = True
        elif tag == 'tr':
            self.current_row = []
        elif tag in ('td', 'th'):
            self.current_row.append("")
        elif tag == 'hr':
            safe_insert(self.widget, tk.END, "─" * 40 + "\n", "md_hr")
        elif tag == 'a':
            self.current_tags.append('md_link')

    def handle_endtag(self, tag):
        if self.tag_stack and self.tag_stack[-1] == tag:
            self.tag_stack.pop()
            
        if tag in ('h1', 'h2', 'h3', 'strong', 'b', 'em', 'i', 'blockquote', 'li', 'a'):
            if tag == 'blockquote':
                safe_insert(self.widget, tk.END, "\n")
            elif tag in ('h1', 'h2', 'h3', 'li'):
                safe_insert(self.widget, tk.END, "\n")
            
            map_tag = {
                'h1': 'md_h1', 'h2': 'md_h2', 'h3': 'md_h3',
                'strong': 'md_bold', 'b': 'md_bold',
                'em': 'md_italic', 'i': 'md_italic',
                'blockquote': 'md_blockquote', 'li': 'md_list',
                'a': 'md_link'
            }.get(tag)
            if map_tag in self.current_tags:
                self.current_tags.remove(map_tag)
                
        elif tag == 'code':
            self.in_code = False
            if 'code_block' in self.current_tags:
                self.current_tags.remove('code_block')
                code_content = "".join(self.code_text)
                self.code_text = []
                
                if self.code_lang:
                    safe_insert(self.widget, tk.END, f"  {self.code_lang}\n", "code_lang")
                
                start_idx = self.widget.index(tk.END)
                lines = code_content.split("\n")
                if lines and not lines[-1]:
                    lines.pop()
                for line in lines:
                    safe_insert(self.widget, tk.END, f"  {line}\n", "code_block")
                end_idx = self.widget.index(tk.END)
                _apply_syntax_highlighting(self.widget, start_idx, end_idx)
                safe_insert(self.widget, tk.END, "\n")
                self.code_lang = ""
            elif 'md_inline_code' in self.current_tags:
                self.current_tags.remove('md_inline_code')
                
        elif tag in ('ul', 'ol'):
            if self.list_counters:
                self.list_counters.pop()
        elif tag == 'thead':
            self.in_thead = False
        elif tag == 'tr':
            self.table_rows.append((list(self.current_row), self.in_thead))
        elif tag == 'table':
            self.in_table = False
            self._render_parsed_table()
        elif tag == 'p':
            if 'blockquote' not in self.tag_stack:
                safe_insert(self.widget, tk.END, "\n")
        elif tag == 'br':
            safe_insert(self.widget, tk.END, "\n")

    def handle_data(self, data):
        if self.in_table:
            if any(t in ('td', 'th') for t in self.tag_stack) and self.current_row:
                self.current_row[-1] += data
        elif self.in_code and 'pre' in self.tag_stack:
            self.code_text.append(data)
        else:
            tags = tuple(self.current_tags) if self.current_tags else ('ai_text',)
            safe_insert(self.widget, tk.END, data, tags)

    def _render_parsed_table(self):
        if not self.table_rows:
            return
        
        max_cols = max(len(row) for row, _ in self.table_rows)
        if max_cols == 0:
            return
        col_widths = [0] * max_cols
        for row, _ in self.table_rows:
            for j, cell in enumerate(row):
                col_widths[j] = max(col_widths[j], len(cell))
                
        for idx, (row, is_header) in enumerate(self.table_rows):
            tag = "md_table_header" if is_header else "md_table"
            line_parts = []
            for j in range(max_cols):
                cell = row[j] if j < len(row) else ""
                line_parts.append(cell.ljust(col_widths[j]))
            safe_insert(self.widget, tk.END, "  │ " + " │ ".join(line_parts) + " │\n", tag)
            
            if is_header:
                sep_parts = ["─" * w for w in col_widths]
                safe_insert(self.widget, tk.END, "  ├─" + "─┼─".join(sep_parts) + "─┤\n", "md_table")
        safe_insert(self.widget, tk.END, "\n")


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


def render_markdown(widget, text, colors):
    """Parse markdown text using python-markdown and render into a tkinter Text widget."""
    html = markdown.markdown(text, extensions=['fenced_code', 'tables'])
    parser = HTMLToTkinterParser(widget, colors)
    parser.feed(html)




