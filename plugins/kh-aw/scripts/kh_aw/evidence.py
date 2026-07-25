from __future__ import annotations

import html
import re
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from .util import read_json, sha256_file, slug, utc_now, write_json

SEARCH_HOSTS = {"duckduckgo.com", "www.google.com", "google.com", "bing.com", "www.bing.com", "search.naver.com"}


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() in {"script", "style", "noscript", "svg", "canvas"}:
            self.skip += 1

    def handle_endtag(self, tag):
        if tag.lower() in {"script", "style", "noscript", "svg", "canvas"} and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            text = re.sub(r"\s+", " ", data).strip()
            if text:
                self.parts.append(text)

    def text(self) -> str:
        return "\n".join(self.parts)


def extract_text(raw: bytes, content_type: str = "") -> str:
    decoded = raw.decode("utf-8", errors="replace")
    if "html" not in content_type.lower() and not re.search(r"<html|<body|<!doctype", decoded[:2000], re.I):
        return re.sub(r"\n{3,}", "\n\n", decoded).strip()
    parser = TextExtractor()
    parser.feed(decoded)
    return html.unescape(parser.text()).strip()


def register_source(
    run_root: Path,
    *,
    element_id: str,
    source_type: str,
    url: str,
    body_file: Path,
    title: str = "",
    query: str = "",
    http_status: int = 200,
    project_fit_reason: str = "",
    license_note: str = "",
    retrieval_mode: str = "registered-local-body",
    retrieval_session_id: str = "",
    retrieval_evidence_file: Path | None = None,
) -> dict[str, Any]:
    source_type = source_type.lower().strip()
    if source_type not in {"web", "github", "official"}:
        raise ValueError("source_type must be web, github, or official")
    body_file = body_file.resolve()
    raw = body_file.read_bytes()
    content_type = "text/html" if body_file.suffix.lower() in {".html", ".htm"} else "text/plain"
    text = extract_text(raw, content_type)
    source_id = f"SRC-{slug(element_id).upper()}-{sha256_file(body_file)[:12].upper()}"
    evidence_dir = run_root / "evidence" / "bodies" / slug(element_id)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    raw_target = evidence_dir / f"{source_id}{body_file.suffix.lower() or '.body'}"
    text_target = evidence_dir / f"{source_id}.txt"
    if body_file != raw_target:
        raw_target.write_bytes(raw)
    text_target.write_text(text, encoding="utf-8", newline="\n")
    retrieval_evidence_path = ""
    retrieval_evidence_sha256 = ""
    if retrieval_evidence_file is not None:
        retrieval_evidence_file = retrieval_evidence_file.resolve()
        if not retrieval_evidence_file.is_file():
            raise ValueError("retrieval evidence file does not exist")
        try:
            retrieval_evidence_path = retrieval_evidence_file.relative_to(run_root.resolve()).as_posix()
        except ValueError as exc:
            raise ValueError("retrieval evidence must stay inside run root") from exc
        retrieval_evidence_sha256 = sha256_file(retrieval_evidence_file)
    record = {
        "id": source_id,
        "elementId": element_id,
        "sourceType": source_type,
        "url": url,
        "title": title,
        "query": query,
        "httpStatus": int(http_status),
        "bodyPath": raw_target.relative_to(run_root).as_posix(),
        "bodySha256": sha256_file(raw_target),
        "bodyBytes": len(raw),
        "textPath": text_target.relative_to(run_root).as_posix(),
        "extractedCharacters": len(text),
        "excerpt": re.sub(r"\s+", " ", text)[:1200],
        "projectFitReason": project_fit_reason,
        "licenseNote": license_note,
        "retrievalMode": retrieval_mode,
        "retrievalSessionId": retrieval_session_id,
        "retrievalEvidencePath": retrieval_evidence_path,
        "retrievalEvidenceSha256": retrieval_evidence_sha256,
        "fetchedAt": utc_now(),
        "evidenceType": "direct-body-extraction",
        "textSha256": sha256_file(text_target),
        "accepted": int(http_status) >= 200 and int(http_status) < 400 and len(text.strip()) >= 500 and len(raw) >= 500,
    }
    registry_path = run_root / "evidence" / "source-registry.json"
    registry = read_json(registry_path, {"schemaVersion": "3.0", "sources": []})
    sources = registry.setdefault("sources", [])
    sources = [item for item in sources if item.get("id") != source_id and not (item.get("elementId") == element_id and item.get("url") == url)]
    sources.append(record)
    registry["sources"] = sources
    registry["updatedAt"] = utc_now()
    write_json(registry_path, registry)
    return record


def fetch_url_to_evidence(
    run_root: Path,
    *,
    element_id: str,
    source_type: str,
    url: str,
    query: str = "",
    project_fit_reason: str = "",
    license_note: str = "",
    timeout: int = 30,
) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "KH_Aw-research-evidence/2.0 (+https://github.com/addpyun78)",
            "Accept": "text/html,application/json,text/plain;q=0.9,*/*;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(5 * 1024 * 1024 + 1)
            status = getattr(response, "status", 200)
            content_type = response.headers.get("Content-Type", "")
            title = response.headers.get("X-Title", "")
    except urllib.error.HTTPError as error:
        raw = error.read()
        status = error.code
        content_type = error.headers.get("Content-Type", "") if error.headers else ""
        title = ""
    if len(raw) > 5 * 1024 * 1024:
        raise ValueError("Fetched body exceeds 5 MiB evidence limit")
    suffix = ".html" if "html" in content_type.lower() else ".txt"
    temp = run_root / "evidence" / "incoming" / f"{slug(element_id)}-{slug(urllib.parse.urlparse(url).netloc)}{suffix}"
    temp.parent.mkdir(parents=True, exist_ok=True)
    temp.write_bytes(raw)
    record = register_source(
        run_root,
        element_id=element_id,
        source_type=source_type,
        url=url,
        body_file=temp,
        title=title,
        query=query,
        http_status=status,
        project_fit_reason=project_fit_reason,
        license_note=license_note,
        retrieval_mode="live-fetch",
    )
    temp.unlink(missing_ok=True)
    return record
