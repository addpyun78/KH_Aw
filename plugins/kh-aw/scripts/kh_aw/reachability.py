from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

from .util import utc_now


ROUTE_PATTERN = re.compile(r"""(?:path|route|url)\s*[:=(]\s*["']([^"']+)["']""", re.I)


def analyze_source_reachability(project_root: Path) -> dict[str, Any]:
    root = project_root.resolve()
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, str]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in {".git", "node_modules", ".kh_aw", "build", "dist"} for part in path.parts):
            continue
        if path.suffix.lower() not in {".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".json"}:
            continue
        relative = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        nodes[relative] = {"id": relative, "type": "source", "routes": ROUTE_PATTERN.findall(text)}
        if path.suffix == ".py":
            try:
                tree = ast.parse(text)
            except SyntaxError:
                continue
            for item in ast.walk(tree):
                if isinstance(item, (ast.Import, ast.ImportFrom)):
                    names = [alias.name for alias in item.names]
                    for name in names:
                        edges.append({"from": relative, "to": name, "kind": "import"})
        else:
            for match in re.finditer(r"""(?:import|require\()\s*(?:[^"']*from\s*)?["']([^"']+)["']""", text):
                edges.append({"from": relative, "to": match.group(1), "kind": "import"})
    entrypoints = [
        node_id for node_id in nodes
        if Path(node_id).name.lower() in {"main.py", "app.py", "index.js", "index.ts", "main.tsx", "main.jsx", "index.html"}
    ]
    return {
        "schemaVersion": "4.0", "generatedAt": utc_now(), "projectRoot": root.as_posix(),
        "entrypoints": entrypoints, "nodes": list(nodes.values()), "edges": edges,
        "unreachableReviewRequired": True,
    }
