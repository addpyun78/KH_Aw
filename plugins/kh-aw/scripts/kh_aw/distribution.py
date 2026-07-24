from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

EXPECTED_VERSION = "3.2.0"
EXPECTED_SKILLS = {
    "kh-aw-audit-upgrade",
    "kh-aw-full-cycle",
    "kh-aw-implementation-repair",
    "kh-aw-multi-agent-orchestration",
    "kh-aw-release-company",
    "kh-aw-research-design",
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
    "scripts/kh_aw/distribution.py",
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
}
FORBIDDEN_PARTS = {"node_modules", "__pycache__", ".playwright", "browser-profile", "user-data-dir"}


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
    actual_skills = {path.name for path in skills_root.iterdir() if path.is_dir()} if skills_root.is_dir() else set()
    if actual_skills != EXPECTED_SKILLS:
        errors.append(f"skill set mismatch: expected={sorted(EXPECTED_SKILLS)} actual={sorted(actual_skills)}")
    for skill in EXPECTED_SKILLS:
        if not (skills_root / skill / "SKILL.md").is_file():
            errors.append(f"skill missing SKILL.md: {skill}")
        if not (skills_root / skill / "agents" / "openai.yaml").is_file():
            errors.append(f"skill missing agents/openai.yaml: {skill}")

    manifest = _load_json(plugin_root / ".codex-plugin" / "plugin.json", errors, "plugin manifest")
    package = _load_json(plugin_root / "package.json", errors, "package.json")
    marketplace = _load_json(marketplace_root / ".agents" / "plugins" / "marketplace.json", errors, "marketplace manifest")
    if manifest:
        if manifest.get("name") != "kh-aw":
            errors.append("plugin manifest name must be kh-aw")
        if manifest.get("version") != EXPECTED_VERSION:
            errors.append(f"plugin manifest version must be {EXPECTED_VERSION}")
        interface = manifest.get("interface", {})
        if not isinstance(interface, dict) or interface.get("displayName") != "KH_Aw":
            errors.append("plugin displayName must be KH_Aw")
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
        if len(tests) < 37:
            errors.append(f"enforcement test count is too low: {len(tests)} < 37")

    for path in marketplace_root.rglob("*"):
        rel_parts = set(path.relative_to(marketplace_root).parts)
        if rel_parts & FORBIDDEN_PARTS:
            errors.append(f"forbidden runtime/cache path in distribution: {path.relative_to(marketplace_root).as_posix()}")
        if path.is_file() and path.suffix == ".pyc":
            errors.append(f"compiled Python cache forbidden in distribution: {path.relative_to(marketplace_root).as_posix()}")

    return sorted(set(errors))
