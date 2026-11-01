"""Pure text search and bounded, lightweight syntax tokenization."""

import keyword
import re


HIGHLIGHT_LIMIT = 200_000
PY_PATTERN = re.compile(
    r'#[^\n]*|(?:"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\')|\b(?:'
    + '|'.join(keyword.kwlist) + r')\b', re.MULTILINE)
JS_PATTERN = re.compile(
    r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|\b(?:function|const|let|var|return|if|else|class|import|export|true|false|null)\b')
JSON_PATTERN = re.compile(r'"(?:\\.|[^"\\])*"|\b(?:true|false|null)\b')


def find_next(text, needle, start=0):
    if not needle:
        return None
    match = re.search(re.escape(needle), text[max(0, start):], re.IGNORECASE)
    if match:
        begin = max(0, start) + match.start()
        return begin, begin + len(match.group())
    match = re.search(re.escape(needle), text[:max(0, start)], re.IGNORECASE)
    return (match.start(), match.end()) if match else None


def replace_all(text, needle, replacement):
    if not needle:
        return text, 0
    return re.subn(re.escape(needle), lambda _: replacement, text,
                   flags=re.IGNORECASE)


def syntax_spans(text, suffix):
    """Return (tag, start, end) offsets; unknown/large text stays plain."""
    if len(text) > HIGHLIGHT_LIMIT:
        return []
    suffix = suffix.lower()
    if suffix == '.py':
        pattern = PY_PATTERN
    elif suffix in ('.js', '.jsx', '.ts', '.tsx'):
        pattern = JS_PATTERN
    elif suffix == '.json':
        pattern = JSON_PATTERN
    else:
        return []
    return [(('comment' if m.group().startswith(('#', '//')) else
              'string' if m.group()[0] in '\"\'' else 'keyword'),
             m.start(), m.end()) for m in pattern.finditer(text)]
