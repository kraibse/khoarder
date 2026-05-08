"""HTML → markdown extraction layers.

Trafilatura is the primary normalizer. Readability and lxml are fallbacks for
pages where trafilatura returns nothing. The Wikipedia path is kept as a
dedicated fast extractor because the existing implementation is known-good
and Wikipedia content trips false-positives in the bot-challenge classifier.
"""
from __future__ import annotations

import logging
import re
from html.parser import HTMLParser

from app.services.imports.meta import extract_meta
from app.services.imports.types import ExtractionResult, QualityScore

logger = logging.getLogger(__name__)


def _quality(body: str) -> QualityScore:
    chars = len(body.strip())
    paragraphs = sum(1 for line in body.split("\n\n") if line.strip())
    return QualityScore(body_chars=chars, paragraphs=paragraphs)


def _coerce(html: str, base_url: str, body: str, extractor: str) -> ExtractionResult:
    title, excerpt, img = extract_meta(html, base_url)
    if not excerpt and body:
        first = body.split("\n\n")[0].strip()
        if len(first) > 20:
            excerpt = first[:280]
    return ExtractionResult(
        title=title or base_url,
        excerpt=excerpt,
        body=body.strip(),
        has_img=bool(img),
        img_url=img,
        quality=_quality(body),
        extractor=extractor,
    )


# ── Math preprocessor — preserve LaTeX through extraction ───────────────────
def _preprocess_math(html: str) -> str:
    """Inline KaTeX/MathJax/MathML LaTeX source as `$...$` text.

    Trafilatura strips `<math>` and the surrounding katex/MathJax wrappers by
    default, so equations vanish. We pull the LaTeX source out of the
    `<annotation encoding="application/x-tex">` node (KaTeX, MathJax v3, MathML
    semantics) or `<script type="math/tex">` (MathJax v2) and replace the whole
    math wrapper with a plain text node containing the raw LaTeX. Pages without
    embedded LaTeX source (rendered-only MathML, image equations) are left
    untouched.
    """
    try:
        from lxml.html import fromstring, tostring
    except ImportError:
        return html
    if "<annotation" not in html and "math/tex" not in html and "<math" not in html:
        return html
    try:
        doc = fromstring(html)
    except Exception:
        return html

    def _looks_like_math_wrapper(el) -> bool:
        tag = el.tag if isinstance(el.tag, str) else ""
        if tag in ("math", "semantics", "mrow"):
            return True
        if tag.startswith("mjx") or tag.startswith("mml"):
            return True
        cls = el.get("class") or ""
        return "katex" in cls or "MathJax" in cls or "mjx-" in cls

    def _replace_with_text(el, text: str) -> None:
        parent = el.getparent()
        if parent is None:
            return
        tail = el.tail or ""
        prev = el.getprevious()
        if prev is not None:
            prev.tail = (prev.tail or "") + text + tail
        else:
            parent.text = (parent.text or "") + text + tail
        parent.remove(el)

    # KaTeX / MathJax v3 / MathML-with-semantics
    for ann in doc.xpath('//annotation[@encoding="application/x-tex"]'):
        latex = (ann.text_content() or "").strip()
        if not latex:
            continue
        anchor = ann
        for ancestor in ann.iterancestors():
            if _looks_like_math_wrapper(ancestor):
                anchor = ancestor
            else:
                break
        cls = anchor.get("class") or ""
        is_display = "katex-display" in cls or anchor.get("display") == "block"
        wrapped = f"\n\n$$ {latex} $$\n\n" if is_display else f" ${latex}$ "
        _replace_with_text(anchor, wrapped)

    # MathJax v2
    for script in doc.xpath('//script[starts-with(@type, "math/tex")]'):
        latex = (script.text or "").strip()
        if not latex:
            continue
        is_display = "display" in (script.get("type") or "")
        wrapped = f"\n\n$$ {latex} $$\n\n" if is_display else f" ${latex}$ "
        _replace_with_text(script, wrapped)

    return tostring(doc, encoding="unicode")


# ── Trafilatura — the workhorse ─────────────────────────────────────────────
def extract_with_trafilatura(html: str, base_url: str) -> ExtractionResult | None:
    try:
        import trafilatura
    except ImportError:
        return None
    try:
        body = trafilatura.extract(
            html,
            url=base_url,
            include_comments=False,
            include_tables=True,
            include_links=True,
            include_images=False,
            favor_recall=True,
            with_metadata=False,
            output_format="markdown",
        )
    except Exception as exc:
        logger.debug("trafilatura failed for %s: %s", base_url, exc)
        return None
    if not body or len(body.strip()) < 80:
        return None
    return _coerce(html, base_url, body, "trafilatura")


# ── Readability — fallback for sites where trafilatura returns nothing ──────
def extract_with_readability(html: str, base_url: str) -> ExtractionResult | None:
    try:
        from readability import Document
        import html as html_lib
    except ImportError:
        return None
    try:
        doc = Document(html)
        summary_html = doc.summary()
    except Exception as exc:
        logger.debug("readability failed for %s: %s", base_url, exc)
        return None
    clean = re.sub(r"<[^>]+>", " ", summary_html)
    clean = html_lib.unescape(clean)
    clean = re.sub(r" {2,}", " ", clean)
    clean = re.sub(r"\n{3,}", "\n\n", clean).strip()
    if len(clean) < 80:
        return None
    result = _coerce(html, base_url, clean, "readability")
    rd_title = ""
    try:
        rd_title = doc.title() or ""
    except Exception:
        pass
    if rd_title:
        result.title = rd_title
    return result


# ── lxml XPath — last resort for non-standard layouts ───────────────────────
_XPATHS = (
    "//article",
    "//main",
    '//*[@role="main"]',
    '//*[@id="content"]',
    '//*[contains(@class,"article-body")]',
    '//*[contains(@class,"article-content")]',
    '//*[contains(@class,"entry-content")]',
    '//*[contains(@class,"post-content")]',
    '//*[contains(@class,"content-body")]',
    '//*[contains(@class,"page-content")]',
    '//*[contains(@class,"story-body")]',
    '//*[contains(@class,"body-content")]',
)


def extract_with_lxml(html: str, base_url: str) -> ExtractionResult | None:
    try:
        from lxml.html import fromstring
    except ImportError:
        return None
    try:
        doc = fromstring(html.encode("utf-8", errors="replace"))
        for tag in ("script", "style", "nav", "footer", "header", "aside", "noscript"):
            for el in doc.findall(f".//{tag}"):
                p = el.getparent()
                if p is not None:
                    p.remove(el)
        content = None
        for xpath in _XPATHS:
            els = doc.xpath(xpath)
            if els:
                content = max(els, key=lambda e: len((e.text_content() or "")))
                break
        if content is None:
            body_el = doc.find(".//body")
            content = body_el if body_el is not None else doc
        parts: list[str] = []
        seen: set[str] = set()
        for el in content.iter():
            tag = el.tag if isinstance(el.tag, str) else ""
            if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                text = (el.text_content() or "").strip()
                if text and text not in seen and len(text) > 2:
                    seen.add(text)
                    parts.append(f"\n{'#' * int(tag[1])} {text}\n")
            elif tag == "p":
                text = (el.text_content() or "").strip()
                if len(text) > 30 and text not in seen:
                    seen.add(text)
                    parts.append(text + "\n\n")
        body = re.sub(r"\n{3,}", "\n\n", "".join(parts)).strip()
    except Exception as exc:
        logger.debug("lxml extraction failed for %s: %s", base_url, exc)
        return None
    if len(body) < 80:
        return None
    return _coerce(html, base_url, body, "lxml")


# ── Wikipedia fast path ─────────────────────────────────────────────────────
class _WikiStripper(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip = 0
        self.in_p = False
        self.in_h = False
        self.hlevel = 0

    def handle_starttag(self, tag, attrs):
        ad = dict(attrs)
        if tag in ("script", "style", "nav", "footer", "header", "aside"):
            self.skip += 1
        elif tag == "p":
            cls = ad.get("class", "")
            self.in_p = not any(c in cls for c in ("reference", "navbox", "infobox", "mw-empty-elt"))
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.in_h = True
            self.hlevel = int(tag[1])
        elif tag in ("br", "div"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav", "footer", "header", "aside"):
            self.skip -= 1
        elif tag == "p":
            if self.in_p and self.skip == 0:
                self.parts.append("\n\n")
            self.in_p = False
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            if self.in_h and self.skip == 0:
                self.parts.append("\n\n")
            self.in_h = False

    def handle_data(self, data):
        if self.skip:
            return
        if self.in_h:
            prefix = "#" * self.hlevel + " "
            self.parts.append((prefix if not self.parts or self.parts[-1].endswith("\n") else "") + data)
        elif self.in_p:
            self.parts.append(data)

    def get_text(self) -> str:
        return re.sub(r"\n\s*\n", "\n\n", "".join(self.parts)).strip()


def extract_wikipedia(html: str, base_url: str) -> ExtractionResult:
    """Targeted extractor for Wikipedia's `mw-content-text` div."""
    content_match = re.search(
        r'<div[^>]*id=["\']mw-content-text["\'][^>]*>(.*?)</div>\s*'
        r'(?:<div[^>]*class=["\']catlinks["\']|<div[^>]*id=["\']mw-data-after-content["\']|</body>)',
        html,
        re.IGNORECASE | re.DOTALL,
    )
    feed = content_match.group(1) if content_match else html
    s = _WikiStripper()
    s.feed(feed)
    body = s.get_text()
    return _coerce(html, base_url, body, "wikipedia")


# ── Orchestrated extraction ─────────────────────────────────────────────────
def extract_best(html: str, base_url: str, *, is_wikipedia: bool = False) -> ExtractionResult:
    """Run the cheapest extractor that yields a usable body. Always returns *something*."""
    html = _preprocess_math(html)
    if is_wikipedia:
        return extract_wikipedia(html, base_url)

    candidates: list[ExtractionResult] = []
    for fn in (extract_with_trafilatura, extract_with_readability, extract_with_lxml):
        result = fn(html, base_url)
        if result is None:
            continue
        candidates.append(result)
        if result.quality.is_good():
            return result

    if candidates:
        return max(candidates, key=lambda r: r.quality.body_chars)

    # All extractors empty — return the meta-only stub so the caller can decide
    # whether to escalate or surface a partial import.
    return _coerce(html, base_url, "", "none")
