"""Selective publisher-document context; source excerpts remain immutable snapshots."""

import asyncio
import ipaddress
import re
import socket
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

import httpx


def pdf_context(content: bytes, excerpt: str) -> dict:
    import fitz
    with fitz.open(stream=content, filetype="pdf") as document:
        terms = set(re.findall(r"[a-z]{4,}", excerpt.lower()))
        texts = [page.get_text() for page in document]
        scores = [len(terms & set(re.findall(r"[a-z]{4,}", text.lower()))) for text in texts]
        selected = sorted(sorted(range(len(texts)), key=lambda i: (-scores[i], i))[:2])
        sections = []
        for index in selected:
            page = document[index]
            # Align words by their printed baseline and horizontal coordinates. This
            # preserves multilevel table headings that reading-order text flattens.
            lines = []
            for word in sorted(page.get_text("words"), key=lambda item: (item[1], item[0])):
                line = next((row for row in reversed(lines[-3:]) if abs(row[0] - word[1]) < 2), None)
                if line is None:
                    line = [word[1], []]
                    lines.append(line)
                line[1].append(word)
            rendered = []
            for _, words in sorted(lines):
                text = ""
                for word in sorted(words, key=lambda item: item[0]):
                    column = round(word[0] / 4)
                    text += " " * max(1 if text else 0, column - len(text)) + word[4]
                rendered.append(text)
            sections.append({"page": index + 1, "text": "\n".join(rendered), "method": "pdf-coordinate-lines"})
        return {"sections": sections, "page_count": len(document), "selected_pages": [index + 1 for index in selected],
                "coverage": "selected_pages", "layout_preserved": True}


class _PublisherHTML(HTMLParser):
    """Keep table cells/spans and heading context instead of flattening columns."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.sections, self.headings, self.metadata = [], [], {}
        self.hidden = 0
        self.block = None
        self.parts = []
        self.table = None
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"script", "style", "nav", "noscript"}:
            self.hidden += 1
        if self.hidden:
            return
        if tag == "meta":
            key = attrs.get("property") or attrs.get("name")
            if key in {"article:published_time", "article:modified_time", "date", "datePublished"}:
                self.metadata[key] = attrs.get("content")
        if tag == "table":
            self.table = {"heading_path": list(self.headings), "rows": [], "caption": ""}
        elif self.table is not None and tag == "tr":
            self.row = []
        elif self.table is not None and tag in {"td", "th"}:
            self.cell = {"text": "", "header": tag == "th", "rowspan": attrs.get("rowspan", "1"),
                         "colspan": attrs.get("colspan", "1"), "scope": attrs.get("scope")}
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "caption"}:
            self.block, self.parts = tag, []
        if tag == "br":
            self.handle_data(" ")

    def handle_data(self, data):
        if self.hidden:
            return
        if self.cell is not None:
            self.cell["text"] += data
        elif self.block:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag in {"script", "style", "nav", "noscript"}:
            self.hidden = max(0, self.hidden - 1)
            return
        if self.hidden:
            return
        if tag in {"td", "th"} and self.cell is not None:
            self.cell["text"] = " ".join(self.cell["text"].split())
            if self.row is not None:
                self.row.append(self.cell)
            self.cell = None
        elif tag == "tr" and self.row is not None and self.table is not None:
            self.table["rows"].append(self.row)
            self.row = None
        elif tag == "table" and self.table is not None:
            import json
            self.sections.append({**self.table, "method": "html-table-cells",
                "text": json.dumps(self.table, ensure_ascii=False)})
            self.table = None
        elif tag == self.block:
            text = " ".join("".join(self.parts).split())
            if tag.startswith("h"):
                level = int(tag[1])
                self.headings = self.headings[:level - 1] + [text]
            elif tag == "caption" and self.table is not None:
                self.table["caption"] = text
            elif text:
                self.sections.append({"heading_path": list(self.headings), "text": text, "method": "html-passage"})
            self.block, self.parts = None, []


def html_context(content, excerpt):
    parser = _PublisherHTML()
    parser.feed(content)
    terms = set(re.findall(r"[a-z]{4,}", excerpt.lower()))
    scores = [len(terms & set(re.findall(r"[a-z]{4,}", row["text"].lower()))) for row in parser.sections]
    matches = sorted(range(len(scores)), key=lambda i: (-scores[i], i))[:2]
    # Keep adjacent caveats and table footnotes, not only the matching number.
    selected = sorted({j for i in matches if scores[i] for j in (i - 1, i, i + 1) if 0 <= j < len(scores)})
    return {"sections": [dict(parser.sections[i], section=i + 1) for i in selected],
            "coverage": "selected_html_sections" if selected else "excerpt_only",
            "layout_preserved": True, "publisher_metadata": parser.metadata,
            "section_count": len(scores)}


async def fetch_document_context(url, excerpt):
    from .portfolio_sources import public_url
    async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
        for _ in range(5):
            if not public_url(url):
                raise ValueError("Non-public source URL")
            parsed = urlsplit(url)
            addresses = await asyncio.to_thread(socket.getaddrinfo, parsed.hostname, parsed.port or 443)
            if not addresses or any(not ipaddress.ip_address(row[4][0]).is_global for row in addresses):
                raise ValueError("Non-public source address")
            async with client.stream("GET", url) as response:
                if response.is_redirect:
                    url = urljoin(url, response.headers["location"])
                    continue
                response.raise_for_status()
                chunks, size = [], 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > 20 * 1024 * 1024:
                        raise ValueError("Publisher document exceeds download allowance; original excerpt retained")
                    chunks.append(chunk)
                content = b"".join(chunks)
                if content.startswith(b"%PDF"):
                    result = await asyncio.to_thread(pdf_context, content, excerpt)
                elif "html" in response.headers.get("content-type", "").lower():
                    result = await asyncio.to_thread(html_context, content.decode(response.encoding or "utf-8", errors="replace"), excerpt)
                else:
                    raise ValueError("Source is not a supported PDF or HTML document; original excerpt retained")
                return {**result, "url": url, "etag": response.headers.get("etag")}
    raise ValueError("Too many source redirects")


async def fetch_pdf_context(url, excerpt):
    return await fetch_document_context(url, excerpt)
