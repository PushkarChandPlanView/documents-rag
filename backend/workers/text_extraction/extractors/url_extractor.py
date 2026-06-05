"""Fetch a URL and extract readable text from the HTML response."""
import re
from dataclasses import dataclass

import httpx


@dataclass
class ExtractionResult:
    text: str
    page_count: int


def _strip_html(html: str) -> str:
    # Remove script/style blocks
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    # Replace block-level tags with newlines
    html = re.sub(r"<(br|p|div|h[1-6]|li|tr)[^>]*>", "\n", html, flags=re.IGNORECASE)
    # Strip remaining tags
    html = re.sub(r"<[^>]+>", "", html)
    # Collapse whitespace
    lines = [ln.strip() for ln in html.splitlines() if ln.strip()]
    return "\n".join(lines)


def extract_from_url(url: str) -> ExtractionResult:
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        response = client.get(url, headers={"User-Agent": "DocumentIntelligenceBot/1.0"})
        response.raise_for_status()

    content_type = response.headers.get("content-type", "")
    if "text/html" in content_type or "application/xhtml" in content_type:
        text = _strip_html(response.text)
    else:
        text = response.text

    word_count = len(text.split())
    estimated_pages = max(1, word_count // 250)
    return ExtractionResult(text=text, page_count=estimated_pages)
