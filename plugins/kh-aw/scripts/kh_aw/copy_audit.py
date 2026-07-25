from __future__ import annotations

from pathlib import Path
from typing import Any

from .util import iter_files, safe_relative, sha256_file, utc_now, write_json

NATIVE_COPY_EXTENSIONS = {".kt", ".java", ".xml", ".swift", ".m", ".mm"}
NATIVE_SCREEN_MARKERS = (
    "Activity.",
    "Fragment.",
    "ViewModel.",
    "ViewController.",
    "SwiftUIView.",
)
BRIDGE_HINTS = ("bridge", "webview", "firebase", "naver", "gemma", "auth", "storage", "database")


def classify_copied_file(relative_path: str, target_pipeline: str) -> tuple[str, str]:
    lower = relative_path.lower()
    suffix = Path(relative_path).suffix.lower()
    if ".kh_aw/" in lower or lower.startswith(".kh_aw/"):
        return "allowed_reference_file", "KH_Aw internal evidence/reference files are not product copies."
    if any(hint in lower for hint in BRIDGE_HINTS) and suffix in NATIVE_COPY_EXTENSIONS:
        return "allowed_bridge_file", "Native bridge/integration files may be allowed when they are traced and verified."
    if target_pipeline == "app-mobile-webview" and suffix in NATIVE_COPY_EXTENSIONS:
        if any(marker.lower().replace(".", "") in lower.replace(".", "") for marker in NATIVE_SCREEN_MARKERS):
            return "forbidden_bulk_copy", "HTML WebView targets must not bulk-copy native screen/controller files."
        return "unexplained_copy", "Native source copied into an HTML WebView target requires explicit role evidence."
    return "unexplained_copy", "Copied source file requires explicit role evidence."


def build_copy_audit(
    analysis_root: Path,
    product_root: Path,
    out_path: Path,
    *,
    target_pipeline: str,
) -> dict[str, Any]:
    analysis_root = analysis_root.resolve()
    product_root = product_root.resolve()
    source_by_hash: dict[str, list[dict[str, Any]]] = {}
    source_count = 0
    product_count = 0
    copied: list[dict[str, Any]] = []

    for source in iter_files(analysis_root, include_ignored=False):
        source_count += 1
        digest = sha256_file(source)
        source_by_hash.setdefault(digest, []).append({
            "path": safe_relative(source, analysis_root),
            "sizeBytes": source.stat().st_size,
        })

    for product in iter_files(product_root, include_ignored=False):
        product_count += 1
        digest = sha256_file(product)
        matches = source_by_hash.get(digest, [])
        if not matches:
            continue
        rel = safe_relative(product, product_root)
        classification, reason = classify_copied_file(rel, target_pipeline)
        copied.append({
            "productPath": rel,
            "sourceMatches": matches,
            "sha256": digest,
            "sizeBytes": product.stat().st_size,
            "classification": classification,
            "reason": reason,
        })

    forbidden = [item for item in copied if item["classification"] in {"forbidden_bulk_copy", "unexplained_copy"}]
    native_forbidden = [
        item for item in forbidden
        if Path(str(item.get("productPath", ""))).suffix.lower() in NATIVE_COPY_EXTENSIONS
    ]
    payload = {
        "schemaVersion": "3.2",
        "generatedAt": utc_now(),
        "targetPipeline": target_pipeline,
        "analysisRoot": analysis_root.as_posix(),
        "productRoot": product_root.as_posix(),
        "sourceFileCount": source_count,
        "productFileCount": product_count,
        "copiedFileCount": len(copied),
        "forbiddenCopyCount": len(forbidden),
        "nativeForbiddenCopyCount": len(native_forbidden),
        "copiedFiles": copied,
        "omissions": [],
    }
    write_json(out_path, payload)
    return payload

