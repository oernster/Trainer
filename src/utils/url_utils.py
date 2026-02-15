"""URL utilities.

Centralizes URL canonicalization so we can reliably detect duplicates across
the UI (e.g., trailing slashes, www prefixes, fragments, and query ordering).

The goal is *stable equality* for deduplication, not full RFC URL normalization.
"""

from __future__ import annotations

from typing import Iterable, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


_TRACKING_QUERY_KEYS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "utm_id",
    "utm_name",
    "utm_reader",
    "utm_viz_id",
    "utm_pubreferrer",
    "utm_swu",
    "gclid",
    "fbclid",
}


def canonicalize_url(url: str) -> str:
    """Return a canonical form of *url* suitable for de-duplication.

    Rules:
    - lower-case scheme + hostname
    - drop default ports (80 for http, 443 for https)
    - remove common tracking query parameters and sort remaining query params
    - drop fragment
    - normalize trailing slash (strip, except for root path)
    """

    if not url:
        return ""

    parts = urlsplit(url.strip())
    scheme = (parts.scheme or "").lower()

    hostname = (parts.hostname or "").lower()
    # Normalize common host variants
    if hostname.startswith("www."):
        hostname = hostname[4:]

    port = parts.port
    if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        port = None

    netloc = hostname
    if port is not None:
        netloc = f"{hostname}:{port}"

    # Normalize path so that empty path and root path ('/') are considered equal.
    # We choose the *no trailing slash* representation for stability.
    path = (parts.path or "").rstrip("/")

    # Normalize query ordering and drop common tracking keys
    query_pairs = parse_qsl(parts.query, keep_blank_values=True)
    filtered_pairs = [(k, v) for (k, v) in query_pairs if k.lower() not in _TRACKING_QUERY_KEYS]
    filtered_pairs.sort(key=lambda kv: (kv[0].lower(), kv[1]))
    query = urlencode(filtered_pairs, doseq=True)

    return urlunsplit((scheme, netloc, path, query, ""))


def dedupe_urls(urls: Iterable[str]) -> list[str]:
    """Deduplicate URLs preserving the first occurrence (by canonical form)."""

    seen: set[str] = set()
    result: list[str] = []
    for url in urls:
        canon = canonicalize_url(url)
        if not canon or canon in seen:
            continue
        seen.add(canon)
        result.append(url)
    return result


def first_unique_url(candidates: Iterable[str], used_canonical: set[str]) -> Optional[str]:
    """Return the first candidate URL whose canonical form isn't in *used_canonical*.

    Adds the chosen canonical URL to *used_canonical*.
    """

    for url in candidates:
        canon = canonicalize_url(url)
        if not canon or canon in used_canonical:
            continue
        used_canonical.add(canon)
        return url
    return None

