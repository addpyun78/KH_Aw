from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

IGNORED_PARTS = {
    ".git", ".kh_aw", "node_modules", ".gradle", "build", "dist", ".idea",
    ".vscode", "__pycache__", ".pytest_cache", ".next", ".nuxt", "coverage",
}
TEXT_EXTENSIONS = {
    ".txt", ".md", ".markdown", ".json", ".jsonl", ".yaml", ".yml", ".toml",
    ".xml", ".html", ".htm", ".css", ".scss", ".sass", ".less", ".js", ".mjs",
    ".cjs", ".ts", ".tsx", ".jsx", ".py", ".java", ".kt", ".kts", ".gradle",
    ".properties", ".ini", ".cfg", ".conf", ".sh", ".bat", ".ps1", ".sql",
    ".swift", ".dart", ".go", ".rs", ".php", ".rb", ".vue", ".svelte",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def write_json(path: Path, value: Any) -> None:
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    atomic_write_text(path, payload)


def copy_file_atomic(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=str(target.parent))
    os.close(fd)
    try:
        shutil.copy2(source, temp_name)
        os.replace(temp_name, target)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def safe_resolve(path: str | Path, base: Path | None = None) -> Path:
    candidate = Path(path).expanduser()
    if not candidate.is_absolute() and base is not None:
        candidate = base / candidate
    return candidate.resolve()


def is_inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def safe_relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def should_ignore(path: Path, root: Path, extra: Iterable[str] = ()) -> bool:
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        parts = path.parts
    ignored = IGNORED_PARTS | set(extra)
    return any(part in ignored for part in parts)


def iter_files(
    root: Path,
    extra_ignored: Iterable[str] = (),
    *,
    include_ignored: bool = False,
) -> Iterator[Path]:
    root = root.resolve()
    if not root.exists():
        return
    for path in sorted(root.rglob("*"), key=lambda p: p.as_posix().lower()):
        if not path.is_file() or path.is_symlink():
            continue
        if not include_ignored and should_ignore(path, root, extra_ignored):
            continue
        if include_ignored and any(part in set(extra_ignored) for part in path.relative_to(root).parts):
            continue
        yield path


def line_count(path: Path) -> int | None:
    if path.suffix.lower() not in TEXT_EXTENSIONS and path.name not in {"Dockerfile", "Makefile"}:
        return None
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            return sum(1 for _ in handle)
    except OSError:
        return None


def slug(value: str, fallback: str = "item") -> str:
    result = re.sub(r"[^a-z0-9\uac00-\ud7a3]+", "-", str(value).strip().lower()).strip("-")
    return result[:80] or fallback


def nonempty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return bool(value)
    return True


def exact_instruction_lines(text: str) -> list[str]:
    return [line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n") if line.strip()]


def load_state(run_root: Path) -> dict[str, Any]:
    state = read_json(run_root / "state.json")
    if not isinstance(state, dict):
        raise FileNotFoundError(f"KH_Aw state missing: {run_root / 'state.json'}")
    return state


def save_state(run_root: Path, state: dict[str, Any]) -> None:
    state["updatedAt"] = utc_now()
    write_json(run_root / "state.json", state)


def latest_run(workspace_root: Path) -> Path:
    pointer = read_json(workspace_root / "latest-run.json", {})
    run_id = pointer.get("runId") if isinstance(pointer, dict) else None
    if not run_id:
        raise FileNotFoundError("No KH_Aw run exists. Run init first.")
    run_root = workspace_root / "runs" / run_id
    if not run_root.is_dir():
        raise FileNotFoundError(f"Latest KH_Aw run directory is missing: {run_root}")
    return run_root


def unique_nonempty(values: Iterable[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def json_file_hash(path: Path) -> str:
    value = read_json(path, None)
    if value is None:
        return ""
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(canonical)


def write_last_good(source: Path, checkpoint_root: Path, label: str) -> Path:
    target = checkpoint_root / f"{slug(label)}.last-good{source.suffix}"
    copy_file_atomic(source, target)
    return target
