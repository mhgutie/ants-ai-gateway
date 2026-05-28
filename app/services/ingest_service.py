from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

from markitdown import MarkItDown

_md = MarkItDown()


def convert_bytes(content: bytes, filename: str) -> dict:
    suffix = Path(filename).suffix or ".bin"
    started = time.perf_counter()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        result = _md.convert(tmp_path)
    finally:
        os.unlink(tmp_path)
    elapsed = int((time.perf_counter() - started) * 1000)
    return {
        "markdown": result.text_content or "",
        "title": result.title,
        "source_type": suffix.lstrip("."),
        "char_count": len(result.text_content or ""),
        "conversion_time_ms": elapsed,
    }


def convert_url(url: str) -> dict:
    started = time.perf_counter()
    result = _md.convert(url)
    elapsed = int((time.perf_counter() - started) * 1000)
    return {
        "markdown": result.text_content or "",
        "title": result.title,
        "source_type": "url",
        "char_count": len(result.text_content or ""),
        "conversion_time_ms": elapsed,
    }
