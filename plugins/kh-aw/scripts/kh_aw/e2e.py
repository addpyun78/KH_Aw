from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any

from .doctor import run_doctor
from .installation import inspect_installations
from .integrity import TEXT_SUFFIXES
from .packaging import build_deterministic_zip
from .util import utc_now


def _crlf_checkout(root: Path) -> None:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix and path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        path.write_bytes(text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n").encode("utf-8"))


def run_local_e2e(plugin_root: Path) -> dict[str, Any]:
    source = plugin_root.resolve()
    version = __import__("json").loads(
        (source / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
    )["version"]
    cases: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="kh-aw-e2e-") as temp_name:
        temp = Path(temp_name)
        cache = temp / "codex" / "plugins" / "cache" / "market" / "kh-aw" / version
        shutil.copytree(source, cache)
        cache_result = run_doctor(cache, codex_home=temp / "codex")
        cases.append({"id": "versioned-cache-doctor", "pass": cache_result["ok"], "errors": cache_result["errors"]})

        crlf = temp / "crlf" / "kh-aw" / version
        shutil.copytree(source, crlf)
        _crlf_checkout(crlf)
        crlf_result = run_doctor(crlf, codex_home=temp / "empty-home")
        cases.append({"id": "crlf-checkout-doctor", "pass": crlf_result["ok"], "errors": crlf_result["errors"]})

        duplicate_home = temp / "duplicates"
        for market in ("one", "two"):
            target = duplicate_home / "plugins" / "cache" / market / "kh-aw" / version
            shutil.copytree(source, target)
        inventory = inspect_installations(home=duplicate_home)
        cases.append({
            "id": "duplicate-shadow-detection",
            "pass": inventory["shadowingRisk"] and len(inventory["duplicates"]) == 1,
            "errors": [] if inventory["shadowingRisk"] else ["duplicate cache was not detected"],
        })

        first = build_deterministic_zip(source, temp / "one.zip")
        second = build_deterministic_zip(source, temp / "two.zip")
        cases.append({
            "id": "deterministic-zip",
            "pass": first["sha256"] == second["sha256"],
            "errors": [] if first["sha256"] == second["sha256"] else ["ZIP hashes differ"],
        })
    return {
        "schemaVersion": "4.0",
        "checkedAt": utc_now(),
        "pass": all(item["pass"] for item in cases),
        "cases": cases,
    }
