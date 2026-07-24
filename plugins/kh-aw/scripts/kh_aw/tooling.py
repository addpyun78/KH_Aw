from __future__ import annotations

import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from .capabilities import record_capability
from .util import is_inside, read_json, safe_resolve, sha256_file, slug, utc_now, write_json

APK_INSTALL_PATTERNS = [
    re.compile(r"(^|\s)adb(?:\.exe)?\s+[^\n]*\binstall(?:-multiple|-multi-package)?\b", re.I),
    re.compile(r"(^|\s)pm\s+install\b", re.I),
    re.compile(r"\bconnected(?:Debug|Release)?AndroidTest\b", re.I),
    re.compile(r"\binstallDebug\b", re.I),
    re.compile(r"\bbundletool\b[^\n]*\binstall-apks\b", re.I),
]

TOOL_PROBES: dict[str, list[str]] = {
    "python": ["python3", "--version"],
    "git": ["git", "--version"],
    "node": ["node", "--version"],
    "npm": ["npm", "--version"],
    "java": ["java", "-version"],
    "gradle": ["gradle", "--version"],
    "adb": ["adb", "version"],
    "android-emulator": ["emulator", "-version"],
    "sdkmanager": ["sdkmanager", "--version"],
    "xcodebuild": ["xcodebuild", "-version"],
    "simctl": ["xcrun", "simctl", "help"],
}

TARGET_REQUIREMENTS: dict[str, list[dict[str, Any]]] = {
    "web-responsive": [
        {"id": "project-security-scan", "required": True, "kind": "security"},
        {"id": "web-package-install", "required": False, "kind": "dependency"},
        {"id": "web-lint", "required": True, "kind": "command"},
        {"id": "web-unit-test", "required": True, "kind": "command"},
        {"id": "web-build", "required": True, "kind": "command"},
        {"id": "web-playwright-chromium", "required": True, "kind": "browser"},
        {"id": "web-playwright-firefox", "required": True, "kind": "browser"},
        {"id": "web-playwright-webkit", "required": True, "kind": "browser"},
        {"id": "web-accessibility-axe", "required": True, "kind": "accessibility"},
        {"id": "web-responsive-matrix", "required": True, "kind": "responsive"},
        {"id": "web-console-network", "required": True, "kind": "runtime"},
        {"id": "web-visual-regression", "required": True, "kind": "visual"},
        {"id": "web-lighthouse", "required": True, "kind": "performance"},
    ],
    "android-native": [
        {"id": "project-security-scan", "required": True, "kind": "security"},
        {"id": "android-gradle-build", "required": True, "kind": "build"},
        {"id": "android-unit-test", "required": True, "kind": "test"},
        {"id": "android-lint", "required": True, "kind": "lint"},
        {"id": "android-screenshot-test", "required": True, "kind": "visual"},
        {"id": "android-emulator-list", "required": True, "kind": "emulator"},
        {"id": "android-emulator-boot", "required": True, "kind": "emulator"},
        {"id": "android-emulator-health", "required": True, "kind": "emulator"},
        {"id": "android-emulator-system-screenshot", "required": True, "kind": "emulator"},
        {"id": "android-logcat-scan", "required": True, "kind": "runtime"},
        {"id": "android-apk-install-excluded", "required": True, "kind": "policy"},
    ],
    "app-mobile-webview": [],
    "ios-native": [
        {"id": "project-security-scan", "required": True, "kind": "security"},
        {"id": "ios-xcodebuild-list", "required": True, "kind": "build"},
        {"id": "ios-build", "required": True, "kind": "build"},
        {"id": "ios-unit-test", "required": True, "kind": "test"},
        {"id": "ios-simulator-list", "required": True, "kind": "simulator"},
        {"id": "ios-simulator-boot", "required": True, "kind": "simulator"},
        {"id": "ios-ui-test", "required": True, "kind": "simulator"},
    ],
    "cross-platform": [],
}
TARGET_REQUIREMENTS["app-mobile-webview"] = TARGET_REQUIREMENTS["web-responsive"] + TARGET_REQUIREMENTS["android-native"]
TARGET_REQUIREMENTS["cross-platform"] = TARGET_REQUIREMENTS["web-responsive"] + TARGET_REQUIREMENTS["android-native"]


def conditional_requirements(project_root: Path | None, target: str) -> list[dict[str, Any]]:
    if project_root is None:
        return []
    root = project_root.resolve()
    result: list[dict[str, Any]] = []
    if (root / "tsconfig.json").is_file() or any(root.glob("tsconfig.*.json")):
        result.append({"id": "web-typecheck", "required": True, "kind": "typecheck", "detectedBy": "tsconfig"})
    if (root / "package-lock.json").is_file() or (root / "npm-shrinkwrap.json").is_file():
        result.append({"id": "web-dependency-audit", "required": True, "kind": "security", "detectedBy": "npm-lock"})
    if (root / "firebase.json").is_file() or (root / ".firebaserc").is_file():
        result.append({"id": "firebase-emulator-suite", "required": True, "kind": "backend-emulator", "detectedBy": "firebase-config"})
    if any((root / name).is_file() for name in ["compose.yml", "compose.yaml", "docker-compose.yml", "docker-compose.yaml"]):
        result.append({"id": "docker-compose-config", "required": True, "kind": "container", "detectedBy": "compose-file"})
    if (root / "pubspec.yaml").is_file():
        result.extend([
            {"id": "flutter-analyze", "required": True, "kind": "lint", "detectedBy": "pubspec"},
            {"id": "flutter-test", "required": True, "kind": "test", "detectedBy": "pubspec"},
            {"id": "flutter-build-apk", "required": True, "kind": "build", "detectedBy": "pubspec", "apkInstallExcluded": True},
        ])
    if any(root.rglob("AndroidManifest.xml")):
        result.extend([
            {"id": "android-manifest-parse", "required": True, "kind": "static-analysis", "detectedBy": "AndroidManifest.xml"},
            {"id": "android-gradle-dependencies", "required": True, "kind": "dependency", "detectedBy": "AndroidManifest.xml"},
        ])
    if (root / "openapi.yaml").is_file() or (root / "openapi.json").is_file():
        result.append({"id": "openapi-contract-validation", "required": True, "kind": "api-contract", "detectedBy": "openapi"})
    return result


def effective_requirements(target: str, project_root: Path | None = None) -> list[dict[str, Any]]:
    requirements: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in TARGET_REQUIREMENTS.get(target, TARGET_REQUIREMENTS["web-responsive"]) + conditional_requirements(project_root, target):
        tool_id = str(item.get("id", ""))
        if not tool_id or tool_id in seen:
            continue
        seen.add(tool_id)
        requirements.append(dict(item))
    return requirements


def tool_policy(target: str, project_root: Path | None = None) -> dict[str, Any]:
    requirements = effective_requirements(target, project_root)
    seen: set[str] = set()
    # effective_requirements already removes duplicate IDs.
    return {
        "schemaVersion": "3.0",
        "generatedAt": utc_now(),
        "targetPipeline": target,
        "apkInstallation": {
            "status": "forbidden",
            "reason": "사용자 지시: APK 설치 제외",
            "forbiddenCommands": [pattern.pattern for pattern in APK_INSTALL_PATTERNS],
        },
        "requiredTools": requirements,
        "configuration": {
            "baseUrl": "",
            "startCommand": "",
            "serverReadyUrl": "",
            "androidAvd": "",
            "androidSerial": "",
            "iosDevice": "",
            "commands": {},
        },
    }


def command_forbidden(command: str) -> str | None:
    for pattern in APK_INSTALL_PATTERNS:
        if pattern.search(command):
            return pattern.pattern
    return None


def _probe(command: list[str], cwd: Path) -> dict[str, Any]:
    executable = shutil.which(command[0])
    if not executable:
        return {"available": False, "command": command, "executable": "", "version": ""}
    try:
        completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True, timeout=20)
        output = (completed.stdout + "\n" + completed.stderr).strip()
        return {
            "available": completed.returncode == 0,
            "command": command,
            "executable": executable,
            "exitCode": completed.returncode,
            "version": output[:4000],
        }
    except Exception as exc:
        return {"available": False, "command": command, "executable": executable, "error": str(exc), "version": ""}


def discover_tools(run_root: Path, project_root: Path) -> dict[str, Any]:
    tools = {tool_id: _probe(command, project_root) for tool_id, command in TOOL_PROBES.items()}
    gradlew = next((path for path in [project_root / "gradlew", project_root / "gradlew.bat"] if path.is_file()), None)
    tools["gradlew"] = {
        "available": bool(gradlew),
        "executable": gradlew.as_posix() if gradlew else "",
        "version": "project wrapper",
    }
    package_json = project_root / "package.json"
    scripts: dict[str, str] = {}
    if package_json.is_file():
        try:
            scripts = json.loads(package_json.read_text(encoding="utf-8")).get("scripts", {}) or {}
        except Exception:
            scripts = {}
    payload = {
        "schemaVersion": "3.0",
        "discoveredAt": utc_now(),
        "platform": {"system": platform.system(), "release": platform.release(), "machine": platform.machine()},
        "projectRoot": project_root.as_posix(),
        "tools": tools,
        "packageScripts": scripts,
    }
    path = run_root / "test" / "tool-discovery.json"
    write_json(path, payload)
    payload["path"] = path.relative_to(run_root).as_posix()
    payload["sha256"] = sha256_file(path)
    return payload


def _artifact_records(project_root: Path, artifacts: list[str]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for raw in artifacts:
        path = safe_resolve(raw, project_root)
        if path.is_file():
            records.append({"path": path.as_posix(), "sha256": sha256_file(path), "bytes": path.stat().st_size})
        elif path.is_dir():
            records.append({"path": path.as_posix(), "sha256": "", "bytes": 0, "directory": True})
        else:
            records.append({"path": path.as_posix(), "missing": True})
    return records


def execute_tool(
    run_root: Path,
    state: dict[str, Any],
    *,
    tool_id: str,
    command: str,
    cwd: Path | None = None,
    timeout: int = 1800,
    artifacts: list[str] | None = None,
    env: dict[str, str] | None = None,
    satisfies_tool_ids: list[str] | None = None,
) -> dict[str, Any]:
    forbidden = command_forbidden(command)
    if forbidden:
        raise ValueError(f"APK installation is forbidden by KH_Aw policy: {forbidden}")
    project_root = Path(str(state.get("projectRoot", "."))).resolve()
    cwd = (cwd or project_root).resolve()
    if not cwd.exists():
        raise FileNotFoundError(cwd)
    report_path = run_root / "test" / "test-report.json"
    report = read_json(report_path, {})
    executions = report.setdefault("toolExecutions", [])
    execution_id = f"TOOL-{len(executions) + 1:04d}-{slug(tool_id)}"
    logs = run_root / "test" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    log_path = logs / f"{execution_id}.log"
    started = utc_now()
    started_clock = time.monotonic()
    run_env = os.environ.copy()
    run_env.update(env or {})
    timed_out = False
    try:
        completed = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=timeout,
            env=run_env,
        )
        exit_code = completed.returncode
        stdout, stderr = completed.stdout, completed.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        exit_code = 124
        stdout = exc.stdout or ""
        stderr = (exc.stderr or "") + f"\nTIMEOUT after {timeout}s"
    duration_ms = int((time.monotonic() - started_clock) * 1000)
    log_path.write_text(
        f"EXECUTION_ID: {execution_id}\nTOOL_ID: {tool_id}\nSTARTED_AT: {started}\nCWD: {cwd}\nCOMMAND: {command}\nTIMEOUT_SECONDS: {timeout}\n\nSTDOUT\n{stdout}\n\nSTDERR\n{stderr}\n",
        encoding="utf-8",
        newline="\n",
    )
    record = {
        "executionId": execution_id,
        "toolId": tool_id,
        "satisfiesToolIds": list(satisfies_tool_ids or [tool_id]),
        "command": command,
        "cwd": cwd.as_posix(),
        "startedAt": started,
        "finishedAt": utc_now(),
        "durationMs": duration_ms,
        "exitCode": exit_code,
        "timedOut": timed_out,
        "logPath": log_path.relative_to(run_root).as_posix(),
        "logSha256": sha256_file(log_path),
        "artifacts": _artifact_records(project_root, list(artifacts or [])),
        "apkInstallExcluded": True,
        "status": "passed" if exit_code == 0 else "failed",
    }
    executions.append(record)
    # Backward-compatible command evidence; still bound to the physical execution record.
    report.setdefault("commands", []).append({
        "executionId": execution_id,
        "toolId": tool_id,
        "satisfiesToolIds": list(satisfies_tool_ids or [tool_id]),
        "command": command,
        "cwd": cwd.as_posix(),
        "exitCode": exit_code,
        "outputPath": record["logPath"],
        "outputSha256": record["logSha256"],
        "recordedAt": record["finishedAt"],
    })
    write_json(report_path, report)
    return record


def _git_fallback(run_root: Path, state: dict[str, Any], capability_id: str) -> dict[str, Any]:
    project = Path(str(state.get("projectRoot", "."))).resolve()
    command = "git status --short && git diff --check && git diff --stat"
    record = execute_tool(run_root, state, tool_id="native-fallback-git-diff", command=command, cwd=project, timeout=120)
    if record["exitCode"] == 0:
        evidence = run_root / record["logPath"]
        return record_capability(run_root, capability_id=capability_id, mode="fallback", evidence_file=evidence, invocation=command, tool_execution_ids=[record["executionId"]])
    # Greenfield/non-Git fallback: compare the initialization inventory with current physical hashes.
    initial_path = run_root / "inventory" / "inventory.jsonl"
    initial: dict[str, str] = {}
    if initial_path.is_file():
        for line in initial_path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict) and item.get("path"):
                initial[str(item["path"])] = str(item.get("sha256", ""))
    current: dict[str, str] = {}
    excluded = {str(run_root.resolve()), str(Path(str(state.get("workspaceRoot", ""))).resolve())}
    for path in sorted(project.rglob("*")):
        if not path.is_file():
            continue
        resolved = str(path.resolve())
        if any(resolved == root or resolved.startswith(root + os.sep) for root in excluded if root):
            continue
        rel = path.relative_to(project).as_posix()
        current[rel] = sha256_file(path)
    payload = {
        "schemaVersion": "3.0",
        "generatedAt": utc_now(),
        "mode": "physical-hash-diff",
        "added": sorted(path for path in current if path not in initial),
        "removed": sorted(path for path in initial if path not in current),
        "changed": sorted(path for path in current if path in initial and current[path] != initial[path]),
        "unchangedCount": sum(1 for path in current if path in initial and current[path] == initial[path]),
    }
    evidence = run_root / "reports" / "native-capabilities" / f"{slug(capability_id)}-physical-diff.json"
    write_json(evidence, payload)
    return record_capability(run_root, capability_id=capability_id, mode="fallback", evidence_file=evidence, invocation="KH_Aw physical SHA-256 diff fallback", tool_execution_ids=[])


def exercise_capability(run_root: Path, state: dict[str, Any], capability_id: str) -> dict[str, Any]:
    project = Path(str(state.get("projectRoot", "."))).resolve()
    if capability_id in {"codex-diff-implement", "codex-diff-review", "codex-diff-release"}:
        return _git_fallback(run_root, state, capability_id)
    evidence_dir = run_root / "reports" / "native-capabilities"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = evidence_dir / f"{slug(capability_id)}.txt"
    tool_ids: list[str] = []
    if capability_id == "codex-plan":
        source = read_json(run_root / "contract" / "requirements.json", {})
        evidence_path.write_text(json.dumps(source, ensure_ascii=False, indent=2), encoding="utf-8")
        invocation = "KH_Aw requirements/state-machine plan fallback"
    elif capability_id == "codex-context":
        source = {
            "state": read_json(run_root / "state.json", {}),
            "inventory": read_json(run_root / "inventory" / "inventory-summary.json", {}),
        }
        evidence_path.write_text(json.dumps(source, ensure_ascii=False, indent=2), encoding="utf-8")
        invocation = "KH_Aw physical context inventory fallback"
    elif capability_id.startswith("codex-agents-"):
        stage = capability_id.removeprefix("codex-agents-")
        dispatch = run_root / "orchestration" / stage / "dispatch-manifest.json"
        payload = read_json(dispatch, {}) if dispatch.is_file() else {"stage": stage, "status": "dispatch-manifest-missing"}
        evidence_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        invocation = "KH_Aw physical subagent dispatch manifest fallback; this fallback does not count as completed AI workers"
    elif capability_id == "codex-artifact-analysis":
        paths = [run_root / "inventory" / "inventory-summary.json", run_root / "analysis" / "analysis-ledger.json"]
        evidence_path.write_text("\n".join(f"{p.relative_to(run_root)} {sha256_file(p) if p.is_file() else 'MISSING'}" for p in paths), encoding="utf-8")
        invocation = "KH_Aw analysis artifact hash inventory"
    elif capability_id == "codex-web-research":
        registry = run_root / "evidence" / "source-registry.json"
        evidence_path.write_text(registry.read_text(encoding="utf-8") if registry.is_file() else "MISSING source registry", encoding="utf-8")
        invocation = "KH_Aw body extraction source registry fallback"
    elif capability_id == "codex-artifact-design":
        paths = list((run_root / "design").rglob("*"))
        evidence_path.write_text("\n".join(f"{p.relative_to(run_root)} {sha256_file(p) if p.is_file() else 'DIR'}" for p in paths), encoding="utf-8")
        invocation = "KH_Aw every-page mockup artifact inventory"
    elif capability_id == "codex-review":
        paths = [run_root / "review" / "review.json"] + list((run_root / "review" / "screenshots").glob("*.png"))
        evidence_path.write_text("\n".join(f"{p.relative_to(run_root)} {sha256_file(p) if p.is_file() else 'MISSING'}" for p in paths), encoding="utf-8")
        invocation = "KH_Aw browser/runtime review evidence fallback"
    elif capability_id == "codex-test":
        report = run_root / "test" / "test-report.json"
        evidence_path.write_text(report.read_text(encoding="utf-8") if report.is_file() else "MISSING test report", encoding="utf-8")
        invocation = "KH_Aw physical toolchain report fallback"
    elif capability_id == "codex-hooks":
        events = run_root / "reports" / "gate-events.jsonl"
        if not events.is_file():
            events.write_text(json.dumps({"event": "hook-fallback-initialized", "at": utc_now()}, ensure_ascii=False) + "\n", encoding="utf-8")
        evidence_path.write_text(events.read_text(encoding="utf-8"), encoding="utf-8")
        invocation = "KH_Aw gate event hook fallback"
    elif capability_id == "codex-artifact-release":
        paths = [run_root / "release" / "release.json"] + list((run_root / "release").glob("*"))
        evidence_path.write_text("\n".join(f"{p.relative_to(run_root)} {sha256_file(p) if p.is_file() else 'DIR'}" for p in paths), encoding="utf-8")
        invocation = "KH_Aw release artifact hash inventory"
    else:
        raise ValueError(f"no fallback implementation for capability: {capability_id}")
    return record_capability(run_root, capability_id=capability_id, mode="fallback", evidence_file=evidence_path, invocation=invocation, tool_execution_ids=tool_ids)


def _npm_script(scripts: dict[str, str], names: list[str]) -> str | None:
    for name in names:
        if name in scripts:
            return f"npm run {shlex.quote(name)}"
    return None


def suggested_commands(target: str, project_root: Path, discovery: dict[str, Any], config: dict[str, Any]) -> dict[str, str]:
    scripts = discovery.get("packageScripts", {}) if isinstance(discovery, dict) else {}
    commands: dict[str, str] = dict(config.get("commands", {}) or {})
    if target in {"web-responsive", "app-mobile-webview", "cross-platform"}:
        commands.setdefault("web-lint", _npm_script(scripts, ["lint", "check"]) or "npx eslint .")
        commands.setdefault("web-unit-test", _npm_script(scripts, ["test", "test:unit"]) or "npm test -- --runInBand")
        commands.setdefault("web-build", _npm_script(scripts, ["build"]) or "npm run build")
    if target in {"android-native", "app-mobile-webview", "cross-platform"}:
        wrapper = "gradlew.bat" if os.name == "nt" else "./gradlew"
        commands.setdefault("android-gradle-build", f"{wrapper} --no-daemon assembleDebug")
        commands.setdefault("android-unit-test", f"{wrapper} --no-daemon testDebugUnitTest")
        commands.setdefault("android-lint", f"{wrapper} --no-daemon lintDebug")
        # Configure this to a real screenshot-test task available in the project (Compose screenshot, Paparazzi, Roborazzi, etc.).
        commands.setdefault("android-screenshot-test", f"{wrapper} --no-daemon verifyPaparazziDebug")
        commands.setdefault("android-emulator-list", "emulator -list-avds")
        commands.setdefault("android-emulator-health", "adb devices -l && adb shell getprop sys.boot_completed && adb shell wm size")
        commands.setdefault("android-logcat-scan", "adb logcat -d -v threadtime '*:E'")
    if target == "ios-native":
        commands.setdefault("ios-xcodebuild-list", "xcodebuild -list")
        commands.setdefault("ios-simulator-list", "xcrun simctl list devices available")
    if (project_root / "tsconfig.json").is_file() or any(project_root.glob("tsconfig.*.json")):
        commands.setdefault("web-typecheck", _npm_script(scripts, ["typecheck", "check:types"]) or "npx tsc --noEmit")
    if (project_root / "package-lock.json").is_file() or (project_root / "npm-shrinkwrap.json").is_file():
        commands.setdefault("web-dependency-audit", "npm audit --audit-level=high")
    if (project_root / "firebase.json").is_file() or (project_root / ".firebaserc").is_file():
        commands.setdefault("firebase-emulator-suite", _npm_script(scripts, ["test:firebase", "emulators:test"]) or "firebase emulators:exec --project demo-kh-aw 'echo KH_Aw-Firebase-Emulator-Ready'")
    if any((project_root / name).is_file() for name in ["compose.yml", "compose.yaml", "docker-compose.yml", "docker-compose.yaml"]):
        commands.setdefault("docker-compose-config", "docker compose config --quiet")
    if (project_root / "pubspec.yaml").is_file():
        commands.setdefault("flutter-analyze", "flutter analyze")
        commands.setdefault("flutter-test", "flutter test")
        commands.setdefault("flutter-build-apk", "flutter build apk --debug")
    if any(project_root.rglob("AndroidManifest.xml")):
        wrapper = "gradlew.bat" if os.name == "nt" else "./gradlew"
        commands.setdefault("android-gradle-dependencies", f"{wrapper} --no-daemon dependencies")
        manifest = next(project_root.rglob("AndroidManifest.xml"), None)
        if manifest:
            commands.setdefault("android-manifest-parse", f"python3 -c \"import xml.etree.ElementTree as E; E.parse(r'{manifest.as_posix()}'); print('AndroidManifest XML OK')\"")
    if (project_root / "openapi.yaml").is_file():
        commands.setdefault("openapi-contract-validation", "npx @redocly/cli lint openapi.yaml")
    elif (project_root / "openapi.json").is_file():
        commands.setdefault("openapi-contract-validation", "npx @redocly/cli lint openapi.json")
    return commands


def canonical_required_tool_ids(target: str, project_root: Path | None = None) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in effective_requirements(target, project_root):
        tool_id = str(item.get("id", ""))
        if item.get("required") is True and tool_id and tool_id not in seen:
            seen.add(tool_id)
            result.append(tool_id)
    return result


def required_tool_ids(
    run_root: Path,
    target: str | None = None,
    project_root: Path | None = None,
) -> list[str]:
    if target:
        return canonical_required_tool_ids(target, project_root)
    policy = read_json(run_root / "contract" / "tool-policy.json", {})
    configured = [
        str(item.get("id", ""))
        for item in policy.get("requiredTools", [])
        if isinstance(item, dict) and item.get("required") is True and item.get("id")
    ]
    if configured:
        return configured
    return canonical_required_tool_ids(
        str(policy.get("targetPipeline", "web-responsive")),
        project_root,
    )


def bootstrap_tooling(run_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    project = Path(str(state.get("projectRoot", "."))).resolve()
    discovery = discover_tools(run_root, project)
    policy_path = run_root / "contract" / "tool-policy.json"
    policy = read_json(policy_path, {})
    policy["targetPipeline"] = str(state.get("targetPipeline", "web-responsive"))
    policy["requiredTools"] = effective_requirements(policy["targetPipeline"], project)
    config = policy.setdefault("configuration", {})
    config["commands"] = suggested_commands(str(state.get("targetPipeline", "web-responsive")), project, discovery, config)
    target = str(state.get("targetPipeline", "web-responsive"))
    if target in {"web-responsive", "app-mobile-webview", "cross-platform"}:
        scripts = discovery.get("packageScripts", {})
        if not config.get("baseUrl"):
            config["baseUrl"] = "http://127.0.0.1:4173"
        if not config.get("serverReadyUrl"):
            config["serverReadyUrl"] = config["baseUrl"]
        if not config.get("startCommand"):
            if "preview" in scripts:
                config["startCommand"] = "npm run preview -- --host 127.0.0.1 --port 4173"
            elif "dev" in scripts:
                config["startCommand"] = "npm run dev -- --host 127.0.0.1 --port 4173"
            elif "start" in scripts:
                config["startCommand"] = "npm run start -- --host 127.0.0.1 --port 4173"
            elif (project / "index.html").is_file():
                config["startCommand"] = "python3 -m http.server 4173 --bind 127.0.0.1"
    write_json(policy_path, policy)
    return {"discovery": discovery, "policy": policy}
