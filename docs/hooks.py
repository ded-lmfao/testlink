"""
MkDocs hook: transform RST directives rendered as raw text by mkdocstrings
into styled HTML elements.

Handles:
  - ``.. container:: operations`` / ``.. describe::``  → operations table
  - ``.. warning::`` / ``.. note::`` / etc.            → admonitions
  - ``.. code:: LANG``                                 → syntax-highlighted block
"""

from __future__ import annotations

import html
import re
import shutil
from pathlib import Path

# ---------------------------------------------------------------------------
# Pygments for .. code:: blocks (already installed via mkdocstrings[python])
# ---------------------------------------------------------------------------
try:
    from pygments import highlight as _pyg_highlight
    from pygments.formatters import HtmlFormatter as _HtmlFormatter
    from pygments.lexers import TextLexer as _TextLexer
    from pygments.lexers import get_lexer_by_name as _get_lexer
    from pygments.util import ClassNotFound as _ClassNotFound

    _PYGMENTS_OK = True
    _FORMATTER = _HtmlFormatter(nowrap=True)
except ImportError:
    _PYGMENTS_OK = False

# ---------------------------------------------------------------------------
# Generic RST-directive pattern emitted by mkdocstrings
#
#   <p>.. DIRECTIVE::</p>
#   <div ...highlight...><pre><span></span><code>CONTENT</code></pre></div>
# ---------------------------------------------------------------------------

_DIRECTIVE_RE = re.compile(
    r"<p>\.\. (?P<directive>[a-z]+)(?:::? ?(?P<arg>[^<]*?))?</p>\s*"
    r'<div[^>]*class="[^"]*highlight[^"]*"[^>]*>'
    r"<pre[^>]*><span></span><code>(?P<body>.*?)</code></pre></div>",
    re.DOTALL,
)

# Separate variant: directive with no following code block (bare <p>.. note::</p>)
# — handled inside the main callback anyway since body will be empty.

# ---------------------------------------------------------------------------
# RST inline-markup conversion (applied to admonition body text)
# ---------------------------------------------------------------------------

# :role:`~prefix.Name`  →  <code>Name</code>   (tilde strips the prefix)
_ROLE_SHORT_RE = re.compile(r":[a-z]+:`~[^`]*\.([^`]+)`")
# :role:`full.Path`     →  <code>full.Path</code>
_ROLE_FULL_RE = re.compile(r":[a-z]+:`([^`]+)`")
# ``inline code``
_CODE_RE = re.compile(r"``(.+?)``")
# **bold**
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
# *italic*
_ITALIC_RE = re.compile(r"\*(.+?)\*")


def _rst_to_html(raw: str) -> str:
    """Convert a plain RST text chunk (already HTML-unescaped) to safe HTML."""
    # Escape for HTML output first, then apply inline-markup transforms.
    text = html.escape(raw)

    text = _ROLE_SHORT_RE.sub(lambda m: f"<code>{html.escape(m.group(1))}</code>", text)
    text = _ROLE_FULL_RE.sub(lambda m: f"<code>{m.group(1)}</code>", text)
    text = _CODE_RE.sub(lambda m: f"<code>{m.group(1)}</code>", text)
    text = _BOLD_RE.sub(lambda m: f"<strong>{m.group(1)}</strong>", text)
    text = _ITALIC_RE.sub(lambda m: f"<em>{m.group(1)}</em>", text)

    # Split on blank lines → paragraphs; single newlines → spaces.
    paragraphs = re.split(r"\n{2,}", text.strip())
    parts: list[str] = []
    for para in paragraphs:
        lines = [ln.strip() for ln in para.splitlines() if ln.strip()]
        # Detect a simple bullet list (lines starting with - or * after strip)
        _bullet_re = r"^[-*]\s+"
        if lines and re.match(r"^[-*]\s", lines[0]):
            items = "".join(f"<li>{re.sub(_bullet_re, '', ln)}</li>" for ln in lines)
            parts.append(f"<ul>{items}</ul>")
        else:
            parts.append("<p>" + " ".join(lines) + "</p>")

    return "".join(parts)


# ---------------------------------------------------------------------------
# .. container:: operations
# ---------------------------------------------------------------------------

_DESCRIBE_RE = re.compile(
    r"\.\. describe:: (.+?)\n(.*?)(?=\.\. describe::|\Z)",
    re.DOTALL,
)


def _build_operations(body: str) -> str:
    plain = html.unescape(body)
    items: list[str] = []
    for m in _DESCRIBE_RE.finditer(plain):
        sig = m.group(1).strip()
        desc = m.group(2).strip()
        items.append(
            f'<div class="revv-op-item">'
            f'<code class="revv-op-sig">{html.escape(sig)}</code>'
            f'<span class="revv-op-desc">{html.escape(desc)}</span>'
            f"</div>"
        )
    if not items:
        return ""
    return (
        '<div class="revv-operations">'
        '<div class="revv-operations-label">Supported operations</div>' + "".join(items) + "</div>"
    )


# ---------------------------------------------------------------------------
# .. warning:: / .. note::
# ---------------------------------------------------------------------------

_ADMONITION_META: dict[str, tuple[str, str]] = {
    # directive  →  (css-modifier, label)
    "warning": ("warning", "Warning"),
    "note": ("note", "Note"),
    "hint": ("hint", "Hint"),
    "tip": ("tip", "Tip"),
    "important": ("important", "Important"),
    "caution": ("caution", "Caution"),
    "danger": ("danger", "Danger"),
}

_ADMON_ICON: dict[str, str] = {
    "warning": "⚠",
    "note": "ℹ",
    "hint": "💡",
    "tip": "💡",
    "important": "❗",
    "caution": "⚠",
    "danger": "🔥",
}


def _build_admonition(directive: str, body: str) -> str:
    meta = _ADMONITION_META.get(directive)
    if not meta:
        return ""
    modifier, label = meta
    icon = _ADMON_ICON.get(directive, "ℹ")
    plain = html.unescape(body)
    inner = _rst_to_html(plain)
    return (
        f'<div class="revv-admonition revv-admonition--{modifier}">'
        f'<div class="revv-admonition__title">'
        f'<span class="revv-admonition__icon">{icon}</span>{label}'
        f"</div>"
        f'<div class="revv-admonition__body">{inner}</div>'
        f"</div>"
    )


# ---------------------------------------------------------------------------
# .. code:: LANG
# ---------------------------------------------------------------------------

# Normalise common RST language aliases to Pygments-understood names
_LANG_ALIASES: dict[str, str] = {
    "python3": "python",
    "py": "python",
    "py3": "python",
    "js": "javascript",
    "ts": "typescript",
    "sh": "bash",
    "shell": "bash",
}


def _build_code(lang: str, body: str) -> str:
    plain = html.unescape(body).strip()
    if not plain:
        return ""

    raw_lang = (lang or "text").strip()
    pyg_lang = _LANG_ALIASES.get(raw_lang, raw_lang)
    css_class = f"language-{html.escape(raw_lang)}"

    if _PYGMENTS_OK:
        try:
            lexer = _get_lexer(pyg_lang, stripall=True)
        except _ClassNotFound:
            lexer = _TextLexer()
        highlighted = _pyg_highlight(plain, lexer, _FORMATTER)
    else:
        highlighted = html.escape(plain)

    label = html.escape(raw_lang)
    return (
        f'<div class="revv-code-block">'
        f'<div class="revv-code-header">'
        f'<span class="revv-code-lang-badge">{label}</span>'
        f"</div>"
        f'<div class="{css_class} highlight">'
        f"<pre><span></span><code>{highlighted}</code></pre>"
        f"</div>"
        f"</div>"
    )


# ---------------------------------------------------------------------------
# MkDocs hook entry point
# ---------------------------------------------------------------------------


def on_page_content(html_content: str, **_kwargs) -> str:
    def replace(match: re.Match) -> str:
        directive = match.group("directive")
        body = match.group("body") or ""
        arg = (match.group("arg") or "").strip()

        if directive == "container":
            result = _build_operations(body)
        elif directive == "code":
            result = _build_code(arg, body)
        elif directive in _ADMONITION_META:
            result = _build_admonition(directive, body)
        else:
            return match.group(0)  # unknown directive — leave as-is

        return result if result else match.group(0)

    return _DIRECTIVE_RE.sub(replace, html_content)


def on_post_build(config, **_kwargs) -> None:
    """Ensure Context7 discovery file is available in built docs output."""
    docs_dir = Path(str(config.docs_dir))
    site_dir = Path(str(config.site_dir))

    source = docs_dir / "api" / "context7.json"
    target = site_dir / "api" / "context7.json"

    if not source.exists():
        return

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
