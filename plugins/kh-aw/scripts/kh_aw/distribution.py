from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .util import sha256_file

EXPECTED_VERSION = "4.0.0"
EXPECTED_SKILLS = {
    "kh-aw",
}
REQUIRED_PLUGIN_FILES = {
    ".codex-plugin/plugin.json",
    "PACKAGE_MANIFEST.json",
    "package.json",
    "LICENSE",
    "PRIVACY.md",
    "TERMS.md",
    "scripts/kh_aw_cli.py",
    "scripts/kh_aw/orchestration.py",
    "scripts/kh_aw/gates.py",
    "scripts/kh_aw/repair.py",
    "scripts/kh_aw/tooling.py",
    "scripts/kh_aw/capabilities.py",
    "scripts/kh_aw/contracts.py",
    "scripts/kh_aw/copy_audit.py",
    "scripts/kh_aw/distribution.py",
    "scripts/kh_aw/language_policy.py",
    "scripts/kh_aw/page_inventory.py",
    "scripts/kh_aw/session_forensics.py",
    "scripts/kh_aw/targeting.py",
    "scripts/kh_aw/doctor.py",
    "scripts/kh_aw/installation.py",
    "scripts/kh_aw/runtime.py",
    "scripts/kh_aw/requirement_compiler.py",
    "scripts/kh_aw/reachability.py",
    "scripts/kh_aw/task_graph.py",
    "scripts/kh_aw/claim_verifier.py",
    "scripts/kh_aw/versioning.py",
    "scripts/kh_aw/packaging.py",
    "scripts/kh_aw/e2e.py",
    "scripts/kh_aw/verifier.py",
    "scripts/android_emulator_suite.py",
    "scripts/ios_simulator_suite.py",
    "scripts/web_verify.mjs",
    "scripts/visual_regression.mjs",
    "scripts/lighthouse_check.mjs",
    "scripts/render_mockups.mjs",
    "schemas/native-capability-policy.schema.json",
    "schemas/tool-policy.schema.json",
    "schemas/physical-evidence.schema.json",
    "schemas/test-report.schema.json",
    "schemas/run-lock.schema.json",
    "schemas/subagent-orchestration.schema.json",
    "tests/test_kh_aw.py",
}
REQUIRED_MARKETPLACE_FILES = {
    ".gitattributes",
    "VERSION_LEDGER.json",
    "COMPLETION_CRITERIA_LEDGER.md",
    "TEST_EVIDENCE.md",
    ".agents/plugins/marketplace.json",
    ".github/workflows/kh-aw-ci.yml",
    "README.md",
    "INSTALL_CODEX_WEB.md",
    "GITHUB_PUBLISH.md",
    "PUBLIC_PLUGIN_DIRECTORY.md",
    "FULL_STAGE_REPORT.md",
    "NATIVE_AND_TOOL_ENFORCEMENT_REPORT.md",
    "FINAL_VALIDATION_REPORT.md",
    "FINAL_SCORE_REPORT.md",
    "FINAL_BUILD_NOTICE.md",
    "FINAL_REQUIREMENT_AUDIT.md",
    "FINAL_REQUIREMENT_AUDIT.json",
    "FINAL_SECURITY_SCAN.json",
    "RELEASE_MANIFEST.json",
    "RELEASE_NOTES.md",
    "audit/FULL_INVENTORY_REPORT.md",
    "audit/ORIGINAL_FILE_INVENTORY.csv",
    "audit/ORIGINAL_FILE_INVENTORY.jsonl",
    "audit/ORIGINAL_INVENTORY_SUMMARY.json",
    "audit/CORE_FILE_BY_FILE_REPORT.md",
    "audit/LOGIC_DEEP_RESEARCH_REPORT.md",
    "audit/UPGRADE_MAPPING.md",
    "audit/REQUIREMENTS_TRACEABILITY.md",
    "audit/SCORE_REPORT.md",
    "audit/current/inventory-summary.json",
    "audit/current/inventory.jsonl",
    "audit/current/inventory.csv",
    "audit/current/FULL_PROGRAM_AUDIT.md",
    "design/NEW_ARCHITECTURE.md",
    "docs/BEGINNER_GUIDE_KO.md",
    "docs/INSTALL_UPDATE_REMOVE_KO.md",
    "docs/TROUBLESHOOTING_KO.md",
    "research/OFFICIAL_CODEX_PLUGIN_MODEL.md",
    "research/PUBLIC_PLUGIN_REPOSITORY_LIST.json",
    "research/PUBLIC_PLUGIN_FILE_INVENTORY.jsonl",
    "research/PLUGIN_STRUCTURE_COMPARISON.csv",
    "research/SKILL_ENTRYPOINT_COMPARISON.md",
    "research/SCRIPT_HOOK_MCP_AGENTS_CI_COMPARISON.md",
    "research/INSTALL_CACHE_SHADOWING_COMPARISON.md",
    "research/PLATFORM_CAPABILITY_MATRIX.json",
    "research/PUBLIC_PLUGIN_SUCCESS_PATTERNS.md",
    "research/PUBLIC_PLUGIN_FAILURE_PATTERNS.md",
    "research/KH_AW_STRUCTURAL_DIFFERENCE_REPORT.md",
    "research/SOURCE_CITATION_LEDGER.jsonl",
    "reproduction/REPRODUCTION_MATRIX.md",
    "reproduction/INSTALLATION_SNAPSHOTS.jsonl",
    "reproduction/DOCTOR_RUNS.jsonl",
    "reproduction/ROOT_RESOLUTION_LOGS.jsonl",
    "reproduction/CACHE_SHADOWING_REPORT.md",
    "reproduction/SKILL_VISIBILITY_REPORT.md",
    "reproduction/MANUAL_BYPASS_REPRODUCTION.md",
    "reproduction/ROOT_CAUSE_EVIDENCE.md",
}
FORBIDDEN_PARTS = {"node_modules", "__pycache__", ".playwright", "browser-profile", "user-data-dir"}
INTERNAL_TEXT_SUFFIXES = {".json", ".md", ".mjs", ".py", ".yaml", ".yml"}
INTERNAL_TEXT_EXCLUSIONS: set[str] = set()
USER_FACING_METADATA_FILES = {".codex-plugin/plugin.json"}
HANGUL_PATTERN = re.compile(r"[\uac00-\ud7a3]")
RELEASE_MANIFEST_EXCLUDED_PARTS = {".git", "__pycache__", ".pytest_cache", "node_modules", "dist"}
RELEASE_MANIFEST_EXCLUDED_FILES = {
    "RELEASE_MANIFEST.json",
    "KH_Aw_Codex_Marketplace_v3.2.0_COMPLETE.zip.sha256",
}


def _load_json(path: Path, errors: list[str], label: str) -> dict[str, Any] | None:
    if not path.is_file():
        errors.append(f"missing {label}: {path}")
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        errors.append(f"invalid JSON in {label}: {path}")
        return None
    if not isinstance(payload, dict):
        errors.append(f"{label} must contain a JSON object: {path}")
        return None
    return payload


def _validate_release_manifest(marketplace_root: Path, errors: list[str]) -> None:
    payload = _load_json(marketplace_root / "RELEASE_MANIFEST.json", errors, "release manifest")
    if not payload:
        return
    raw_items = payload.get("files")
    if not isinstance(raw_items, list):
        errors.append("release manifest files must be a list")
        return
    items = {
        str(item.get("path", "")): item
        for item in raw_items
        if isinstance(item, dict) and str(item.get("path", ""))
    }
    physical = {
        path.relative_to(marketplace_root).as_posix(): path
        for path in marketplace_root.rglob("*")
        if path.is_file()
        and path.name not in RELEASE_MANIFEST_EXCLUDED_FILES
        and not set(path.relative_to(marketplace_root).parts) & RELEASE_MANIFEST_EXCLUDED_PARTS
    }
    missing = sorted(set(items) - set(physical))
    uncovered = sorted(set(physical) - set(items))
    if missing:
        errors.append(f"release manifest references missing files: {missing}")
    if uncovered:
        errors.append(f"release manifest does not cover files: {uncovered}")
    for relative in sorted(set(items) & set(physical)):
        item = items[relative]
        path = physical[relative]
        if item.get("sha256") != sha256_file(path) or item.get("bytes") != path.stat().st_size:
            errors.append(f"release manifest hash/size mismatch: {relative}")
    if payload.get("fileCount") != len(items):
        errors.append("release manifest fileCount mismatch")
    if payload.get("totalBytes") != sum(int(item.get("bytes", -1)) for item in items.values()):
        errors.append("release manifest totalBytes mismatch")


def validate_distribution(plugin_root: Path, marketplace_root: Path) -> list[str]:
    plugin_root = plugin_root.resolve()
    marketplace_root = marketplace_root.resolve()
    errors: list[str] = []

    for rel in sorted(REQUIRED_PLUGIN_FILES):
        if not (plugin_root / rel).is_file():
            errors.append(f"distribution missing required plugin file: {rel}")
    for rel in sorted(REQUIRED_MARKETPLACE_FILES):
        if not (marketplace_root / rel).is_file():
            errors.append(f"distribution missing required marketplace file: {rel}")

    skills_root = plugin_root / "skills"
    actual_skills = {
        path.name for path in skills_root.iterdir()
        if path.is_dir() and (path / "SKILL.md").is_file()
    } if skills_root.is_dir() else set()
    if actual_skills != EXPECTED_SKILLS:
        errors.append(f"skill set mismatch: expected={sorted(EXPECTED_SKILLS)} actual={sorted(actual_skills)}")
    for skill in EXPECTED_SKILLS:
        if not (skills_root / skill / "SKILL.md").is_file():
            errors.append(f"skill missing SKILL.md: {skill}")

    manifest = _load_json(plugin_root / ".codex-plugin" / "plugin.json", errors, "plugin manifest")
    package = _load_json(plugin_root / "package.json", errors, "package.json")
    marketplace = _load_json(marketplace_root / ".agents" / "plugins" / "marketplace.json", errors, "marketplace manifest")
    _validate_release_manifest(marketplace_root, errors)
    if manifest:
        if manifest.get("name") != "kh-aw":
            errors.append("plugin manifest name must be kh-aw")
        if manifest.get("version") != EXPECTED_VERSION:
            errors.append(f"plugin manifest version must be {EXPECTED_VERSION}")
        interface = manifest.get("interface", {})
        if not isinstance(interface, dict) or interface.get("displayName") != "KH_Aw":
            errors.append("plugin displayName must be KH_Aw")
        elif not all(HANGUL_PATTERN.search(str(interface.get(field, ""))) for field in ("shortDescription", "longDescription")):
            errors.append("plugin user-facing shortDescription and longDescription must be Korean")
        default_prompts = interface.get("defaultPrompt", []) if isinstance(interface, dict) else []
        if not isinstance(default_prompts, list) or not default_prompts or any(
            any(ord(character) > 127 for character in str(prompt)) for prompt in default_prompts
        ):
            errors.append("plugin Codex-facing defaultPrompt entries must be English ASCII")
    if package and package.get("version") != EXPECTED_VERSION:
        errors.append(f"package.json version must be {EXPECTED_VERSION}")
    if marketplace:
        plugins = marketplace.get("plugins", [])
        match = next((item for item in plugins if isinstance(item, dict) and item.get("name") == "kh-aw"), None)
        if not match:
            errors.append("marketplace is missing kh-aw entry")
        elif match.get("source", {}).get("path") != "./plugins/kh-aw":
            errors.append("marketplace kh-aw source path must be ./plugins/kh-aw")

    test_path = plugin_root / "tests" / "test_kh_aw.py"
    if test_path.is_file():
        tests = re.findall(r"^\s+def test_[A-Za-z0-9_]+\(", test_path.read_text(encoding="utf-8"), re.MULTILINE)
        if len(tests) < 50:
            errors.append(f"enforcement test count is too low: {len(tests)} < 50")

    for path in marketplace_root.rglob("*"):
        rel_parts = set(path.relative_to(marketplace_root).parts)
        if rel_parts & {"__pycache__", ".pytest_cache"}:
            continue
        if rel_parts & FORBIDDEN_PARTS:
            errors.append(f"forbidden runtime/cache path in distribution: {path.relative_to(marketplace_root).as_posix()}")
        if path.is_file() and path.suffix == ".pyc":
            errors.append(f"compiled Python cache forbidden in distribution: {path.relative_to(marketplace_root).as_posix()}")

    for path in plugin_root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in INTERNAL_TEXT_SUFFIXES:
            continue
        relative = path.relative_to(plugin_root).as_posix()
        if (
            relative in INTERNAL_TEXT_EXCLUSIONS
            or relative in USER_FACING_METADATA_FILES
            or relative.endswith("/agents/openai.yaml")
        ):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"Codex-facing text is not valid UTF-8: {relative}")
            continue
        if any(ord(character) > 127 for character in text):
            errors.append(f"Codex-facing package text must use English ASCII content: {relative}")

    return sorted(set(errors))
