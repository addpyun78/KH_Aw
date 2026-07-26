from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def version_ledger(root: Path) -> dict[str, Any]:
    root = root.resolve()
    plugin_root = root / "plugins" / "kh-aw"
    plugin = json.loads((plugin_root / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    package = json.loads((plugin_root / "package.json").read_text(encoding="utf-8"))
    package_manifest = json.loads((plugin_root / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
    root_ledger = json.loads((root / "VERSION_LEDGER.json").read_text(encoding="utf-8"))
    init_text = (plugin_root / "scripts" / "kh_aw" / "__init__.py").read_text(encoding="utf-8")
    init_match = re.search(r'__version__\s*=\s*"([^"]+)"', init_text)
    version = str(plugin.get("version", ""))
    sources = {
        "plugin.json": version,
        "package.json": str(package.get("version", "")),
        "PACKAGE_MANIFEST.json": str(package_manifest.get("version", "")),
        "VERSION_LEDGER.json": str(root_ledger.get("version", "")),
        "kh_aw.__version__": init_match.group(1) if init_match else "",
    }
    return {
        "schemaVersion": "4.0",
        "version": version,
        "sources": sources,
        "consistent": len(set(sources.values())) == 1 and bool(version),
    }
