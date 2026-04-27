"""Cache key for the rendered PDF.

We hash `report.updated_at` plus a version tag. Bump VERSION when the
print template changes so all cached PDFs invalidate at once.
"""
import hashlib

VERSION = "v1"


def build_cache_key(report) -> str:
    """16-char hex hash. Stable for (report, updated_at, VERSION)."""
    raw = f"{VERSION}|{report.pk}|{report.updated_at.isoformat()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
