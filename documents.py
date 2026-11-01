"""UTF-8 document state and failure-safe local file operations."""

from dataclasses import dataclass, field
import os
from pathlib import Path
import re
import stat
import tempfile


MAX_FILE_BYTES = 8_000_000


@dataclass
class Document:
    text: str = ''
    path: Path | None = None
    newline: str = '\n'
    bom: bool = False
    baseline: str = field(init=False)

    def __post_init__(self):
        self.baseline = self.text

    @property
    def dirty(self):
        return self.text != self.baseline


def load_document(path):
    path = Path(path)
    with path.open('rb') as source:
        data = source.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise ValueError(f'File exceeds {MAX_FILE_BYTES:,} byte editor limit')
    bom = data.startswith(b'\xef\xbb\xbf')
    decoded = data[3 if bom else 0:].decode('utf-8', errors='strict')
    first_newline = re.search(r'\r\n|\r|\n', decoded)
    newline = first_newline.group() if first_newline else '\n'
    return Document(decoded.replace('\r\n', '\n').replace('\r', '\n'), path,
                    newline, bom)


def save_document(document, path=None):
    """Commit identity and baseline only after a complete atomic replacement."""
    target = Path(path) if path is not None else document.path
    if target is None:
        raise ValueError('Choose a filename before saving')
    # Atomic replacement would break a symlink alias without changing its target.
    if target.is_symlink():
        raise ValueError('Cannot save through a symbolic link; choose the target file instead')
    encoded = document.text.replace('\n', document.newline).encode('utf-8', 'strict')
    if document.bom:
        encoded = b'\xef\xbb\xbf' + encoded
    if len(encoded) > MAX_FILE_BYTES:
        raise ValueError(f'File exceeds {MAX_FILE_BYTES:,} byte editor limit')
    existing_mode = stat.S_IMODE(target.stat().st_mode) if target.exists() else None
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='wb', dir=target.parent,
                                         prefix=f'.{target.name}.', delete=False) as output:
            temporary = Path(output.name)
            output.write(encoded)
            output.flush()
            os.fsync(output.fileno())
        if existing_mode is not None:
            os.chmod(temporary, existing_mode)
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    document.path = target
    document.baseline = document.text
