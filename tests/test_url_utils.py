from __future__ import annotations

from src.utils.url_utils import canonicalize_url, dedupe_urls


def test_canonicalize_url_strips_fragment_and_trailing_slash_and_www():
    assert (
        canonicalize_url("https://www.example.com/path/#section")
        == "https://example.com/path"
    )


def test_canonicalize_url_sorts_query_and_strips_tracking_params():
    assert (
        canonicalize_url(
            "https://example.com/x?utm_source=a&b=2&a=1&utm_campaign=c#frag"
        )
        == "https://example.com/x?a=1&b=2"
    )


def test_dedupe_urls_preserves_first_occurrence():
    urls = [
        "https://example.com/x/",
        "https://www.example.com/x",
        "https://example.com/y",
    ]
    assert dedupe_urls(urls) == ["https://example.com/x/", "https://example.com/y"]


def test_canonicalize_url_treats_root_paths_equally():
    assert canonicalize_url("https://example.com") == canonicalize_url(
        "https://example.com/"
    )

