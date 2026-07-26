from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse

SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
PLUGIN_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
ALLOWED_TOP = {"id", "name", "version", "description", "skills", "apps", "mcpServers", "interface", "author", "homepage", "repository", "license", "keywords"}
ALLOWED_INTERFACE = {"displayName", "shortDescription", "longDescription", "developerName", "category", "capabilities", "websiteURL", "privacyPolicyURL", "termsOfServiceURL", "brandColor", "composerIcon", "logo", "logoDark", "screenshots", "defaultPrompt", "default_prompt"}


def _asset(plugin_root: Path, raw: Any, field: str, errors: list[str]) -> None:
    if not isinstance(raw, str) or not raw.strip():
        errors.append(f"{field} must be a non-empty relative path")
        return
    posix = PurePosixPath(raw.replace("\\", "/"))
    if posix.is_absolute() or any(part in {"", ".", ".."} for part in posix.parts):
        errors.append(f"{field} must stay inside plugin archive")
        return
    target = (plugin_root / posix.as_posix()).resolve()
    try:
        target.relative_to(plugin_root.resolve())
    except ValueError:
        errors.append(f"{field} escapes plugin archive")
        return
    if not target.is_file():
        errors.append(f"{field} points to missing file: {raw}")


def _https(value: Any, field: str, errors: list[str]) -> None:
    if value is None:
        return
    parsed = urlparse(value) if isinstance(value, str) else None
    if parsed is None or parsed.scheme != "https" or not parsed.netloc:
        errors.append(f"{field} must be an absolute https URL")


def _simple_frontmatter(text: str) -> dict[str, Any] | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end < 0:
        return None
    result: dict[str, Any] = {}
    for raw in text[4:end].splitlines():
        if not raw.strip() or raw.lstrip().startswith("#") or ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value.startswith(('"', "'")) and value.endswith(value[:1]):
            value = value[1:-1]
        if value.lower() == "false":
            result[key] = False
        elif value.lower() == "true":
            result[key] = True
        else:
            result[key] = value
    return result


def validate_plugin(plugin_root: Path) -> list[str]:
    errors: list[str] = []
    plugin_root = plugin_root.resolve()
    manifest_path = plugin_root / ".codex-plugin" / "plugin.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"invalid or missing plugin.json: {exc}"]
    if not isinstance(manifest, dict):
        return ["plugin.json must contain an object"]
    for key in sorted(set(manifest) - ALLOWED_TOP):
        errors.append(f"unsupported plugin.json field: {key}")
    if "[TODO:" in json.dumps(manifest, ensure_ascii=False):
        errors.append("plugin.json contains TODO placeholder")
    name = manifest.get("name")
    if not isinstance(name, str) or not PLUGIN_NAME.fullmatch(name):
        errors.append("plugin name must be lower-case kebab-case")
    version = manifest.get("version")
    versioned_cache_root = plugin_root.parent.name == name and plugin_root.name == version
    if plugin_root.name != name and not versioned_cache_root:
        errors.append("plugin folder name must match plugin.json name")
    if not isinstance(version, str) or not SEMVER.fullmatch(version):
        errors.append("plugin version must be strict semver")
    if not isinstance(manifest.get("description"), str) or not manifest["description"].strip():
        errors.append("plugin field description must be non-empty")
    author = manifest.get("author")
    if not isinstance(author, dict) or not isinstance(author.get("name"), str) or not author["name"].strip():
        errors.append("author.name is required")
    else:
        _https(author.get("url"), "author.url", errors)
        if author.get("email") is not None and (not isinstance(author.get("email"), str) or "@" not in author.get("email", "")):
            errors.append("author.email must be a valid-looking email when present")
    for field in ["homepage", "repository"]:
        _https(manifest.get(field), field, errors)
    skills = str(manifest.get("skills", "")).replace("\\", "/").rstrip("/")
    if skills not in {"skills", "./skills"}:
        errors.append("skills must resolve to skills")
    interface = manifest.get("interface")
    if not isinstance(interface, dict):
        errors.append("interface object is required")
        interface = {}
    for key in sorted(set(interface) - ALLOWED_INTERFACE):
        errors.append(f"unsupported interface field: {key}")
    for field in ["displayName", "shortDescription", "longDescription", "developerName", "category"]:
        if not isinstance(interface.get(field), str) or not interface[field].strip():
            errors.append(f"interface.{field} is required")
    prompts = interface.get("defaultPrompt", interface.get("default_prompt"))
    if not isinstance(prompts, list) or not prompts or any(not isinstance(item, str) or not item.strip() for item in prompts):
        errors.append("interface.defaultPrompt must be a non-empty string array")
    elif len(prompts) > 3:
        errors.append("interface.defaultPrompt must contain at most 3 prompts")
    elif any(len(item) > 128 for item in prompts):
        errors.append("interface.defaultPrompt entries must be at most 128 characters")
    capabilities = interface.get("capabilities")
    if not isinstance(capabilities, list) or not capabilities or any(not isinstance(item, str) or not item.strip() for item in capabilities):
        errors.append("interface.capabilities must be a non-empty string array")
    color = interface.get("brandColor")
    if color is not None and (not isinstance(color, str) or not HEX.fullmatch(color)):
        errors.append("interface.brandColor must be #RRGGBB")
    for field in ["websiteURL", "privacyPolicyURL", "termsOfServiceURL"]:
        _https(interface.get(field), f"interface.{field}", errors)
    for field in ["composerIcon", "logo", "logoDark"]:
        if field in interface:
            _asset(plugin_root, interface[field], f"interface.{field}", errors)
    screenshots = interface.get("screenshots", [])
    if not isinstance(screenshots, list):
        errors.append("interface.screenshots must be an array")
    else:
        for index, item in enumerate(screenshots):
            _asset(plugin_root, item, f"interface.screenshots[{index}]", errors)
    skills_root = plugin_root / "skills"
    if not skills_root.is_dir():
        errors.append("skills directory is missing")
    else:
        for skill_dir in sorted(
            path for path in skills_root.iterdir()
            if path.is_dir() and not path.name.startswith(".") and (path / "SKILL.md").is_file()
        ):
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.is_file():
                errors.append(f"skill {skill_dir.name} missing SKILL.md")
                continue
            text = skill_md.read_text(encoding="utf-8", errors="replace")
            front = _simple_frontmatter(text)
            if not isinstance(front, dict):
                errors.append(f"skill {skill_dir.name} frontmatter invalid or missing")
                continue
            if not str(front.get("name", "")).strip() or not str(front.get("description", "")).strip():
                errors.append(f"skill {skill_dir.name} needs name and description")
            disabled = front.get("disable-model-invocation", front.get("disable_model_invocation"))
            if disabled not in {None, False}:
                errors.append(f"skill {skill_dir.name} disable-model-invocation must be false")
    return errors


def validate_marketplace(root: Path) -> list[str]:
    errors: list[str] = []
    path = root / ".agents" / "plugins" / "marketplace.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"invalid marketplace.json: {exc}"]
    if not isinstance(data, dict) or not isinstance(data.get("plugins"), list):
        return ["marketplace root must contain plugins array"]
    if not isinstance(data.get("name"), str) or not data.get("name"):
        errors.append("marketplace name is required")
    if not isinstance(data.get("interface"), dict) or not data.get("interface", {}).get("displayName"):
        errors.append("marketplace interface.displayName is required")
    names: set[str] = set()
    for entry in data["plugins"]:
        if not isinstance(entry, dict):
            errors.append("marketplace plugin entry must be object")
            continue
        name = entry.get("name")
        if name in names:
            errors.append(f"duplicate marketplace plugin entry: {name}")
        names.add(name)
        expected = root / "plugins" / str(name)
        if not expected.is_dir():
            errors.append(f"marketplace plugin path missing: {expected}")
        source = entry.get("source", {})
        if source.get("source") != "local" or source.get("path") != f"./plugins/{name}":
            errors.append(f"marketplace source for {name} must be ./plugins/{name}")
        policy = entry.get("policy", {})
        if policy.get("installation") not in {"NOT_AVAILABLE", "AVAILABLE", "INSTALLED_BY_DEFAULT"}:
            errors.append(f"invalid installation policy for {name}")
        if policy.get("authentication") not in {"ON_INSTALL", "ON_USE"}:
            errors.append(f"invalid authentication policy for {name}")
        products = policy.get("products")
        if products is not None and (not isinstance(products, list) or not products or any(not isinstance(item, str) for item in products)):
            errors.append(f"invalid products policy for {name}")
        if not entry.get("category"):
            errors.append(f"category missing for {name}")
    return errors
