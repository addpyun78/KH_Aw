from __future__ import annotations

import json
import shutil
import struct
import subprocess
import sys
sys.dont_write_bytecode = True
import tempfile
import unittest
import zlib
import zipfile
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from kh_aw.capabilities import canonical_capability_ids, record_capability
from kh_aw.contracts import STAGES, create_run_contracts, stage_status_passed
from kh_aw.evidence import register_source
from kh_aw.distribution import validate_distribution
from kh_aw.gates import gate_test, run_gate
from kh_aw.inventory import build_inventory
from kh_aw.language_policy import internal_language_issues, korean_ui_character_count
from kh_aw.plugin_validate import validate_plugin
from kh_aw.integrity import build_package_manifest, validate_package_manifest
from kh_aw.installation import inspect_installations, skill_visibility
from kh_aw.packaging import build_deterministic_zip
from kh_aw.requirement_compiler import compile_requirements
from kh_aw.runtime import resume_run
from kh_aw.task_graph import build_task_graph
from kh_aw.orchestration import (
    MIN_SUBAGENTS, MAX_SUBAGENTS, ensure_agent_plan, recommended_subagent_count,
    record_subagent_result, record_lead_aggregation, orchestration_issues,
)
from kh_aw.page_inventory import build_page_candidates
from kh_aw.protection import compare_snapshot, create_protected_snapshot, restore_snapshot
from kh_aw.repair import create_repair_ticket, deterministic_repair
from kh_aw.run_lock import verify_run_lock, write_run_lock
from kh_aw.tooling import canonical_required_tool_ids, command_forbidden, directory_artifact_record, execute_tool, tool_policy
from kh_aw.targeting import infer_target_pipeline
from kh_aw.util import read_json, save_state, sha256_file, write_json


def png(path: Path, width: int = 390, height: int = 844):
    raw = b"".join(b"\x00" + b"\xEE\xEE\xEE" * width for _ in range(height))
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    payload = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


class KHAwTest(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix="kh-aw-test-"))
        self.project = self.temp / "project"
        self.project.mkdir()
        (self.project / "index.html").write_text("<html><body>project</body></html>", encoding="utf-8")
        self.run = self.temp / "run"
        self.run.mkdir()
        self.instructions = "\uccab \ubc88\uc9f8 \uc694\uad6c\uc0ac\ud56d\n\ub450 \ubc88\uc9f8 \uc694\uad6c\uc0ac\ud56d\n"
        create_run_contracts(self.run, self.instructions, "web-responsive")
        build_inventory(self.project, self.run / "inventory")
        self.state = {
            "schemaVersion": "3.0",
            "engineVersion": "3.0.0",
            "runId": "test",
            "projectRoot": self.project.as_posix(),
            "workspaceRoot": (self.temp / "workspace").as_posix(),
            "runRoot": self.run.as_posix(),
            "analysisMode": "analysis-folder-not-provided",
            "analysisFolder": "",
            "analysisSourceRoot": self.project.as_posix(),
            "instructions": self.instructions,
            "instructionsFile": (self.run / "contract" / "user-instructions.txt").as_posix(),
            "targetPipeline": "web-responsive",
            "stageStatus": {stage: "pending" for stage in ["analyze", "research", "design", "implement", "verify", "release"]},
            "repair": {"globalAttempt": 0, "signatures": {}},
        }
        (self.run / "contract" / "user-instructions.txt").write_text(self.instructions, encoding="utf-8")
        write_run_lock(self.run, self.state)
        save_state(self.run, self.state)

    def tearDown(self):
        shutil.rmtree(self.temp, ignore_errors=True)

    def _write_codex_session(self, session_id: str, task_id: str, suffix: str, invocation: str = "") -> Path:
        path = self.temp / ".codex" / "sessions" / "2026" / "07" / "25" / f"rollout-{session_id}-{suffix}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        events = [
            {"type": "session_meta", "payload": {"id": session_id, "taskId": task_id}},
            {"type": "response_item", "payload": {"sessionId": session_id, "taskId": task_id, "invocation": invocation, "text": "physical Codex execution evidence " * 8}},
        ]
        path.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")
        return path

    def test_plugin_manifest_valid(self):
        self.assertEqual(validate_plugin(PLUGIN_ROOT), [])

    def test_analyze_rejects_shallow_placeholder(self):
        gate = run_gate(self.run, self.state, "analyze")
        codes = {item["code"] for item in gate["issues"]}
        self.assertIn("ANALYSIS_FIELD_INCOMPLETE", codes)

    def test_analysis_folder_is_restored(self):
        analysis = self.temp / "analysis"
        analysis.mkdir()
        target = analysis / "source.txt"
        target.write_text("original", encoding="utf-8")
        create_protected_snapshot(analysis, self.run)
        target.write_text("changed", encoding="utf-8")
        self.assertFalse(compare_snapshot(self.run)["ok"])
        self.assertTrue(restore_snapshot(self.run)["ok"])
        self.assertEqual(target.read_text(encoding="utf-8"), "original")

    def test_search_result_page_is_not_evidence(self):
        plan = read_json(self.run / "evidence" / "research-plan.json")
        plan["elements"] = [{
            "id": "E1", "label": "\ub3d9\uc801 \uc2e4\uc81c \uc8fc\uc81c", "category": category,
            "requirementIds": ["REQ-001", "REQ-002"], "webQueries": ["one query", "two query"],
            "githubQueries": ["one github", "two github"], "status": "ready",
        } for category in ["competitor", "feature", "design-system", "image", "font", "icon", "motion", "accessibility", "platform", "conversion"]]
        write_json(self.run / "evidence" / "research-plan.json", plan)
        body = self.temp / "body.html"
        body.write_text("<html><body>" + ("\ubcf8\ubb38 \uc5f0\uad6c \ub0b4\uc6a9 " * 100) + "</body></html>", encoding="utf-8")
        register_source(self.run, element_id="E1", source_type="web", url="https://duckduckgo.com/html/?q=test", body_file=body, project_fit_reason="\ud604\uc7ac \ud504\ub85c\uc81d\ud2b8 \uc694\uad6c\uc640 \ud654\uba74 \uad6c\uc870\ub97c \ube44\uad50\ud558\uae30 \uc704\ud55c \uad6c\uccb4\uc801 \uadfc\uac70\uc785\ub2c8\ub2e4.")
        gate = run_gate(self.run, self.state, "research")
        self.assertIn("SEARCH_RESULT_IS_NOT_BODY_EVIDENCE", {item["code"] for item in gate["issues"]})

    def test_url_only_source_rejected(self):
        registry = {"schemaVersion": "2.0", "sources": [{
            "id": "SRC-1", "elementId": "E1", "sourceType": "web", "url": "https://example.com",
            "bodyPath": "missing.html", "textPath": "missing.txt", "bodySha256": "x", "httpStatus": 200,
            "extractedCharacters": 0, "projectFitReason": "\ud604\uc7ac \ud504\ub85c\uc81d\ud2b8\uc5d0 \ub9e4\uc6b0 \uad6c\uccb4\uc801\uc73c\ub85c \uc801\ud569\ud558\ub2e4\ub294 \ucda9\ubd84\ud55c \uc774\uc720\ub97c \uae30\ub85d\ud569\ub2c8\ub2e4.",
        }]}
        write_json(self.run / "evidence" / "source-registry.json", registry)
        gate = run_gate(self.run, self.state, "research")
        self.assertIn("SOURCE_BODY_MISSING_OR_TOO_SMALL", {item["code"] for item in gate["issues"]})

    def test_design_requires_unique_every_page_mockup(self):
        pages = {"schemaVersion": "2.0", "pages": [{"pageId": "home"}, {"pageId": "detail"}]}
        write_json(self.run / "design" / "page-inventory.json", pages)
        mock = self.run / "design" / "mockups" / "sample.html"
        mock.write_text("<html>home detail " + "content " * 30 + "</html>", encoding="utf-8")
        screen = self.run / "design" / "screenshots" / "sample.png"
        png(screen)
        ledger = read_json(self.run / "design" / "design-ledger.json")
        ledger["visualStructureBoard"] = {"htmlPath": "design/mockups/sample.html", "imagePath": "design/screenshots/sample.png", "pageIds": ["home", "detail"]}
        common = {
            "mockupPath": "design/mockups/sample.html", "screenshotPath": "design/screenshots/sample.png",
            "researchSourceIds": ["S1", "S2"], "layoutRationale": "x" * 30, "visualHierarchy": "x" * 30,
            "typographyStrategy": "x" * 30, "colorStrategy": "x" * 30, "smallBusinessAttentionStrategy": "x" * 30,
            "conversionStrategy": "x" * 30, "accessibilityStrategy": "x" * 30, "states": ["default"],
            "imageStrategy": {"required": True, "reason": "x" * 20, "slots": ["hero"]},
            "motionStrategy": {"required": True, "reason": "x" * 20, "motions": ["enter"], "reducedMotionPlan": "disable"},
        }
        ledger["pages"] = [{"pageId": "home", **common}, {"pageId": "detail", **common}]
        write_json(self.run / "design" / "design-ledger.json", ledger)
        gate = run_gate(self.run, self.state, "design")
        self.assertIn("REPRESENTATIVE_SAMPLE_REUSE_FORBIDDEN", {item["code"] for item in gate["issues"]})

    def test_manual_color_and_concept_keys_removed_by_repair(self):
        ledger = read_json(self.run / "design" / "design-ledger.json")
        ledger["manualConcept"] = "fixed"
        ledger["selectedColors"] = ["red"]
        write_json(self.run / "design" / "design-ledger.json", ledger)
        result = deterministic_repair(self.run, self.state, "design", [])
        cleaned = read_json(self.run / "design" / "design-ledger.json")
        self.assertNotIn("manualConcept", cleaned)
        self.assertNotIn("selectedColors", cleaned)
        self.assertGreater(result["deterministicChanges"], 0)

    def test_repair_ticket_is_nonterminal_and_changes_strategy(self):
        gate = {"issues": [{"code": "SAME_FAILURE", "message": "same"}]}
        generations = []
        for _ in range(4):
            ticket = create_repair_ticket(self.run, self.state, "design", gate, {"actions": []})
            generations.append(ticket["strategyGeneration"])
        self.assertEqual(generations, [1, 1, 1, 2])
        self.assertEqual(read_json(self.run / "state.json")["status"], "repairing")

    def test_implementation_hash_is_physical(self):
        file = self.project / "page.html"
        file.write_text('<div data-motion="MOTION:hero"></div><style>@media (prefers-reduced-motion: reduce){}</style>', encoding="utf-8")
        write_json(self.run / "design" / "page-inventory.json", {"pages": [{"pageId": "home"}]})
        design = read_json(self.run / "design" / "design-ledger.json")
        design["pages"] = [{"pageId": "home", "imageStrategy": {"required": False}, "motionStrategy": {"required": True}}]
        write_json(self.run / "design" / "design-ledger.json", design)
        impl = read_json(self.run / "implementation" / "implementation-ledger.json")
        impl["pages"] = [{"pageId": "home", "targetFiles": ["page.html"], "fileHashes": {"page.html": sha256_file(file)}, "verifiedRegions": ["hero"], "motionIds": ["M1"]}]
        impl["motionImplementations"] = [{"motionId": "M1", "targetFile": "page.html", "implementationMarker": "MOTION:hero", "reducedMotionMarker": "prefers-reduced-motion"}]
        write_json(self.run / "implementation" / "implementation-ledger.json", impl)
        gate = run_gate(self.run, self.state, "implement")
        self.assertNotIn("IMPLEMENTATION_FILE_HASH_MISSING", {item["code"] for item in gate["issues"]})

    def test_cli_advance_returns_nonzero_on_repair(self):
        completed = subprocess.run([sys.executable, str(SCRIPTS / "kh_aw_cli.py"), "advance", "--run-root", str(self.run), "--stage", "analyze"], capture_output=True, text=True)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("repair-required-nonterminal", completed.stdout)

    def test_apk_install_commands_are_forbidden(self):
        self.assertIsNotNone(command_forbidden("adb install app-debug.apk"))
        self.assertIsNotNone(command_forbidden("./gradlew connectedDebugAndroidTest"))
        self.assertIsNotNone(command_forbidden("./gradlew installDebug"))
        self.assertIsNotNone(command_forbidden("bundletool install-apks --apks app.apks"))
        self.assertIsNone(command_forbidden("./gradlew assembleDebug testDebugUnitTest lintDebug"))

    def test_android_policy_requires_real_emulator_but_excludes_install(self):
        policy = tool_policy("android-native")
        ids = {item["id"] for item in policy["requiredTools"] if item["required"]}
        self.assertIn("android-emulator-boot", ids)
        self.assertIn("android-emulator-health", ids)
        self.assertIn("android-emulator-system-screenshot", ids)
        self.assertIn("android-screenshot-test", ids)
        self.assertIn("android-apk-install-excluded", ids)
        self.assertEqual(policy["apkInstallation"]["status"], "forbidden")

    def test_execute_tool_records_physical_log_and_hash(self):
        state = dict(self.state)
        state["projectRoot"] = self.project.as_posix()
        record = execute_tool(self.run, state, tool_id="python-smoke", command=f"{sys.executable} -c \"print('physical-ok')\"", timeout=30)
        log = self.run / record["logPath"]
        self.assertEqual(record["exitCode"], 0)
        self.assertTrue(log.is_file())
        self.assertEqual(record["logSha256"], sha256_file(log))
        self.assertIn("physical-ok", log.read_text(encoding="utf-8"))

    def test_build_artifact_glob_records_recursive_directory_hash(self):
        state = dict(self.state)
        state["projectRoot"] = self.project.as_posix()
        command = (
            f"{sys.executable} -c "
            "\"from pathlib import Path; p=Path('dist'); p.mkdir(exist_ok=True); "
            "(p/'index.html').write_text('<html/>'); (p/'app.js').write_text('void 0'); "
            "(p/'app.css').write_text('body{}')\""
        )
        record = execute_tool(
            self.run,
            state,
            tool_id="web-build",
            command=command,
            artifact_globs=["dist"],
        )
        artifact = record["artifacts"][0]
        self.assertTrue(artifact["directory"])
        self.assertEqual(artifact["fileCount"], 3)
        self.assertEqual(artifact["sha256"], directory_artifact_record(self.project / "dist")["sha256"])
        (self.project / "dist" / "app.js").write_text("changed", encoding="utf-8")
        self.assertNotEqual(artifact["sha256"], directory_artifact_record(self.project / "dist")["sha256"])

    def test_web_build_content_gate_rejects_incomplete_bundle(self):
        build = self.project / "dist"
        build.mkdir()
        (build / "index.html").write_text("<html/>", encoding="utf-8")
        log = self.run / "test" / "logs" / "web-build.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text("build passed", encoding="utf-8")
        report = read_json(self.run / "test" / "test-report.json")
        report["apkInstallationPolicy"] = "forbidden"
        report["toolExecutions"] = [{
            "executionId": "TOOL-WEB-BUILD",
            "toolId": "web-build",
            "satisfiesToolIds": ["web-build"],
            "command": "npm run build",
            "exitCode": 0,
            "status": "passed",
            "timedOut": False,
            "logPath": log.relative_to(self.run).as_posix(),
            "logSha256": sha256_file(log),
            "artifacts": [directory_artifact_record(build)],
        }]
        write_json(self.run / "test" / "test-report.json", report)
        issues = gate_test(self.run, self.state)
        missing_groups = {
            item["evidence"].get("contentGroup")
            for item in issues
            if item["code"] == "WEB_BUILD_CONTENT_MISSING"
        }
        self.assertEqual(missing_groups, {"javascript", "css"})

    def test_webview_apk_gate_inspects_packaged_asset_groups(self):
        apk = self.project / "app-debug.apk"
        with zipfile.ZipFile(apk, "w") as archive:
            archive.writestr("assets/index.html", "<html/>")
        log = self.run / "test" / "logs" / "android-build.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text("assembleDebug passed", encoding="utf-8")
        report = read_json(self.run / "test" / "test-report.json")
        report["apkInstallationPolicy"] = "forbidden"
        report["toolExecutions"] = [{
            "executionId": "TOOL-ANDROID-BUILD",
            "toolId": "android-gradle-build",
            "satisfiesToolIds": ["android-gradle-build"],
            "command": "gradlew.bat assembleDebug",
            "exitCode": 0,
            "status": "passed",
            "timedOut": False,
            "logPath": log.relative_to(self.run).as_posix(),
            "logSha256": sha256_file(log),
            "artifacts": [{"path": apk.as_posix(), "sha256": sha256_file(apk), "bytes": apk.stat().st_size}],
        }]
        write_json(self.run / "test" / "test-report.json", report)
        state = dict(self.state)
        state["targetPipeline"] = "app-mobile-webview"
        issues = gate_test(self.run, state)
        missing_groups = {
            item["evidence"].get("assetGroup")
            for item in issues
            if item["code"] == "WEBVIEW_APK_ASSET_MISSING"
        }
        self.assertEqual(missing_groups, {"css", "javascript", "image"})

    def test_execute_tool_rejects_apk_install(self):
        state = dict(self.state)
        with self.assertRaises(ValueError):
            execute_tool(self.run, state, tool_id="bad", command="adb install app.apk")

    def test_native_capability_requires_session_and_slash(self):
        evidence = self.run / "reports" / "native.txt"
        evidence.parent.mkdir(parents=True, exist_ok=True)
        evidence.write_text("/plan output from actual session", encoding="utf-8")
        with self.assertRaises(ValueError):
            record_capability(self.run, capability_id="codex-plan", mode="native", evidence_file=evidence, invocation="/plan", session_id="")
        fake_session = self.run / "rollout-SESSION-1.jsonl"
        fake_session.write_text(
            json.dumps({"sessionId": "SESSION-1", "invocation": "/plan", "text": "fake " * 40}) + "\n",
            encoding="utf-8",
        )
        with self.assertRaises(ValueError):
            record_capability(
                self.run,
                capability_id="codex-plan",
                mode="native",
                evidence_file=evidence,
                invocation="/plan",
                session_id="SESSION-1",
                session_evidence_file=fake_session,
            )
        session = self._write_codex_session("SESSION-1", "intake", "native-plan", "/plan")
        record = record_capability(
            self.run,
            capability_id="codex-plan",
            mode="native",
            evidence_file=evidence,
            invocation="/plan",
            session_id="SESSION-1",
            session_evidence_file=session,
        )
        self.assertEqual(record["mode"], "native")
        self.assertEqual(record["evidenceSha256"], sha256_file(evidence))
        self.assertEqual(record["sessionEvidenceSha256"], sha256_file(session))

    def test_physical_capability_fallback_is_supported(self):
        evidence = self.run / "evidence" / "fallback-plan.txt"
        evidence.parent.mkdir(parents=True, exist_ok=True)
        evidence.write_text("physical diagnostic fallback output", encoding="utf-8")
        record_capability(
            self.run,
            capability_id="codex-plan",
            mode="fallback",
            evidence_file=evidence,
            invocation="kh-aw-state-plan",
        )
        gate = run_gate(self.run, self.state, "intake")
        self.assertNotIn("NATIVE_SLASH_REQUIRED", {item["code"] for item in gate["issues"]})

    def test_stage_status_prefix_cannot_pass(self):
        self.assertTrue(stage_status_passed("passed"))
        self.assertFalse(stage_status_passed("passed-fake"))
        self.assertFalse(stage_status_passed("passed-awaiting-receipt"))

    def test_status_rejects_complete_state_with_fake_stage_prefix(self):
        gate_rows = []
        for stage in STAGES:
            path = self.run / "reports" / f"gate-{stage}.json"
            write_json(path, {
                "schemaVersion": "3.0",
                "stage": stage,
                "pass": True,
                "issueCount": 0,
                "issues": [],
            })
            gate_rows.append({"stage": stage, "sha256": sha256_file(path)})
        receipt_path = self.run / "release" / "release-receipt.json"
        write_json(receipt_path, {
            "schemaVersion": "3.0",
            "runId": self.state["runId"],
            "status": "complete",
            "gateReports": gate_rows,
        })
        state = read_json(self.run / "state.json")
        state["status"] = "complete"
        state["stageStatus"] = {stage: "passed" for stage in STAGES}
        state["stageStatus"]["design"] = "passed-fake"
        state["releaseReceiptSha256"] = sha256_file(receipt_path)
        save_state(self.run, state)
        completed = subprocess.run(
            [sys.executable, str(SCRIPTS / "kh_aw_cli.py"), "status", "--run-root", str(self.run)],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("not exact approved passed statuses", completed.stdout)

    def test_run_lock_is_checked_outside_intake(self):
        lock_path = self.run / "contract" / "run-lock.json"
        lock = read_json(lock_path)
        lock["internalLanguage"] = "ko-KR"
        write_json(lock_path, lock)
        gate = run_gate(self.run, self.state, "analyze")
        codes = {item["code"] for item in gate["issues"]}
        self.assertTrue({"RUN_LOCK_TAMPERED", "RUN_LOCK_HASH_MISMATCH"} & codes)

    def test_internal_ledgers_must_be_english_but_raw_user_text_is_allowed(self):
        report = read_json(self.run / "analysis" / "analysis-ledger.json")
        report["summary"] = "\ub0b4\ubd80 \ubd84\uc11d \uacb0\uacfc"
        write_json(self.run / "analysis" / "analysis-ledger.json", report)
        self.assertIn(
            "INTERNAL_ARTIFACT_NOT_ENGLISH",
            {item["code"] for item in internal_language_issues(self.run)},
        )
        requirements = read_json(self.run / "contract" / "requirements.json")
        self.assertTrue(any("\uccab \ubc88\uc9f8" in item["requirement"] for item in requirements["requirements"]))

    def test_korean_product_text_is_detected_from_physical_files(self):
        korean = self.project / "korean.html"
        english = self.project / "english.html"
        korean.write_text("<button>\uc800\uc7a5</button><p>\uc624\ub958\uac00 \ubc1c\uc0dd\ud588\uc2b5\ub2c8\ub2e4</p>", encoding="utf-8")
        english.write_text("<button>Save</button>", encoding="utf-8")
        self.assertGreater(korean_ui_character_count([korean]), 0)
        self.assertEqual(korean_ui_character_count([english]), 0)

    def test_gate_writes_physical_hook_event(self):
        run_gate(self.run, self.state, "analyze")
        event_file = self.run / "reports" / "gate-events.jsonl"
        self.assertTrue(event_file.is_file())
        self.assertIn('"event": "gate-completed"', event_file.read_text(encoding="utf-8"))

    def test_contracts_create_native_and_tool_policies(self):
        self.assertTrue((self.run / "contract" / "native-capability-policy.json").is_file())
        policy = read_json(self.run / "contract" / "tool-policy.json")
        self.assertEqual(policy["apkInstallation"]["status"], "forbidden")
        self.assertTrue(policy["requiredTools"])

    def test_freeform_test_claim_is_not_physical_evidence(self):
        report = read_json(self.run / "test" / "test-report.json")
        report["apkInstallationPolicy"] = "forbidden"
        report["accessibilityChecks"] = [{"pass": True, "evidence": "\uac80\uc0ac \uc644\ub8cc"}]
        report["responsiveChecks"] = [{"pass": True, "evidence": "\uac80\uc0ac \uc644\ub8cc"}]
        report["securityChecks"] = [{"pass": True, "evidence": "\uac80\uc0ac \uc644\ub8cc"}]
        report["stateChecks"] = [{"pass": True, "evidence": "\uac80\uc0ac \uc644\ub8cc"}]
        report["performanceChecks"] = [{"pass": True, "evidence": "\uac80\uc0ac \uc644\ub8cc"}]
        report["visualRegressionChecks"] = [{"pass": True, "evidence": "\uac80\uc0ac \uc644\ub8cc"}]
        write_json(self.run / "test" / "test-report.json", report)
        gate = run_gate(self.run, self.state, "test", enforce_order=False)
        codes = {item["code"] for item in gate["issues"]}
        self.assertIn("PHYSICAL_TEST_EVIDENCE_MISSING", codes)

    def test_node_verification_scripts_parse(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node is unavailable")
        for name in ["web_verify.mjs", "visual_regression.mjs", "lighthouse_check.mjs", "render_mockups.mjs"]:
            result = subprocess.run([node, "--check", str(SCRIPTS / name)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_tool_policy_cannot_be_weakened(self):
        policy_path = self.run / "contract" / "tool-policy.json"
        policy = read_json(policy_path)
        policy["requiredTools"] = []
        write_json(policy_path, policy)
        gate = run_gate(self.run, self.state, "intake", enforce_order=False)
        self.assertIn("TARGET_TOOL_POLICY_TAMPERED", {item["code"] for item in gate["issues"]})

    def test_native_capability_policy_cannot_be_weakened(self):
        policy_path = self.run / "contract" / "native-capability-policy.json"
        policy = read_json(policy_path)
        policy["capabilities"] = []
        write_json(policy_path, policy)
        gate = run_gate(self.run, self.state, "intake", enforce_order=False)
        self.assertIn("NATIVE_CAPABILITY_POLICY_TAMPERED", {item["code"] for item in gate["issues"]})

    def test_target_inference_handles_webview_and_web(self):
        webview = infer_target_pipeline("\ubd84\uc11d \ud6c4 HTML \uae30\ubc18 \ubaa8\ubc14\uc77c\uc571 Android WebView \uc571\uc73c\ub85c \uc81c\uc791", self.project)
        self.assertEqual(webview["targetPipeline"], "app-mobile-webview")
        web = infer_target_pipeline("\ud68c\uc0ac \uc18c\uac1c \uc6f9\ud398\uc774\uc9c0\uc640 \ubc18\uc751\ud615 \ub79c\ub529\ud398\uc774\uc9c0 \uc81c\uc791", None)
        self.assertEqual(web["targetPipeline"], "web-responsive")

    def test_dynamic_page_candidates_cover_common_framework_patterns(self):
        source = self.temp / "candidate-source"
        (source / "web").mkdir(parents=True)
        (source / "android").mkdir()
        (source / "flutter").mkdir()
        (source / "web" / "routes.ts").write_text(
            'const routes = [{ path: "/dashboard" }, { path: "/settings" }];',
            encoding="utf-8",
        )
        (source / "android" / "HomeScreen.kt").write_text(
            "@Composable\nfun HomeScreen() { Text(\"Home\") }",
            encoding="utf-8",
        )
        (source / "flutter" / "profile_page.dart").write_text(
            "class ProfilePage extends StatelessWidget {}",
            encoding="utf-8",
        )
        payload = build_page_candidates(source, self.temp / "page-candidates.json")
        kinds = {item["kind"] for item in payload["candidates"]}
        entries = {item["routeOrEntry"] for item in payload["candidates"]}
        self.assertIn("declared-route", kinds)
        self.assertIn("android-compose-screen", kinds)
        self.assertIn("flutter-screen", kinds)
        self.assertIn("/dashboard", entries)

    def test_unknown_target_pipeline_is_blocking(self):
        state = dict(self.state)
        state["targetPipeline"] = "unknown-needs-confirmation"
        gate = run_gate(self.run, state, "intake", enforce_order=False)
        self.assertIn("TARGET_PIPELINE_UNRESOLVED", {item["code"] for item in gate["issues"]})

    def test_goal_capability_is_required_for_every_stage(self):
        policy = read_json(self.run / "contract" / "native-capability-policy.json")
        by_stage = {}
        for item in policy["capabilities"]:
            by_stage.setdefault(item["stage"], set()).add(item["preferredSlash"])
        for stage in ["intake", "analyze", "research", "design", "implement", "review", "test", "release"]:
            self.assertIn("/goal", by_stage[stage])
        required_ids = set(canonical_capability_ids())
        self.assertIn("codex-artifact-research", required_ids)
        self.assertNotIn("codex-hooks", required_ids)

    def test_webview_rejects_bulk_copied_native_legacy_files(self):
        analysis = self.temp / "analysis"
        product = self.temp / "product"
        source = analysis / "app" / "src" / "main" / "java" / "com" / "example" / "CustomerListActivity.kt"
        copied = product / "app" / "src" / "main" / "legacy" / "java" / "com" / "example" / "CustomerListActivity.kt"
        source.parent.mkdir(parents=True, exist_ok=True)
        copied.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("class CustomerListActivity", encoding="utf-8")
        copied.write_text("class CustomerListActivity", encoding="utf-8")
        state = dict(self.state)
        state.update({
            "analysisMode": "analysis-folder-provided",
            "analysisFolder": analysis.as_posix(),
            "projectRoot": product.as_posix(),
            "targetPipeline": "app-mobile-webview",
        })
        write_json(self.run / "design" / "page-inventory.json", {"pages": [{"pageId": "home"}]})
        gate = run_gate(self.run, state, "implement", enforce_order=False)
        self.assertIn("SOURCE_BULK_COPY_DETECTED", {item["code"] for item in gate["issues"]})

    def test_all_json_schemas_parse_and_require_physical_evidence(self):
        schema_root = PLUGIN_ROOT / "schemas"
        names = {path.name for path in schema_root.glob("*.schema.json")}
        self.assertEqual(names, {
            "native-capability-policy.schema.json",
            "tool-policy.schema.json",
            "physical-evidence.schema.json",
            "test-report.schema.json",
            "run-lock.schema.json",
            "subagent-orchestration.schema.json",
        })
        for path in schema_root.glob("*.schema.json"):
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload.get("$schema"), "https://json-schema.org/draft/2020-12/schema")
            self.assertEqual(payload.get("type"), "object")

    def test_conditional_tools_are_detected_and_locked(self):
        (self.project / "tsconfig.json").write_text("{}", encoding="utf-8")
        (self.project / "package-lock.json").write_text("{}", encoding="utf-8")
        (self.project / "firebase.json").write_text("{}", encoding="utf-8")
        ids = set(canonical_required_tool_ids("web-responsive", self.project))
        self.assertIn("web-typecheck", ids)
        self.assertIn("web-dependency-audit", ids)
        self.assertIn("firebase-emulator-suite", ids)

    def test_run_lock_detects_and_repairs_tampering(self):
        lock_path = self.run / "contract" / "run-lock.json"
        lock = read_json(lock_path)
        lock["targetPipeline"] = "android-native"
        write_json(lock_path, lock)
        self.assertTrue(verify_run_lock(self.run, self.state))
        result = deterministic_repair(self.run, self.state, "intake", [{"code": "RUN_LOCK_TAMPERED"}])
        self.assertTrue(any(item.get("action") == "restore-run-lock" for item in result["actions"]))
        self.assertEqual(verify_run_lock(self.run, self.state), [])

    def _complete_intake_agents(self, *, duplicate_output: bool = False):
        plan = ensure_agent_plan(self.run, self.state, "intake", force=True)
        self.assertEqual(plan["selectedSubAgents"], 2)
        worker_ids = []
        for index, assignment in enumerate(plan["assignments"]):
            evidence = self.run / "orchestration" / "intake" / "outputs" / f"worker-{index}.md"
            receipt = self.run / "orchestration" / "intake" / "receipts" / f"worker-{index}.json"
            evidence.parent.mkdir(parents=True, exist_ok=True)
            receipt.parent.mkdir(parents=True, exist_ok=True)
            session_id = f"SUB-SESSION-{index:02d}"
            invocation = f"/agents run {assignment['taskId']}"
            session_evidence = self._write_codex_session(session_id, assignment["taskId"], f"worker-{index}")
            session_evidence_sha = sha256_file(session_evidence)
            review = assignment["reviewTargetWorkerIds"]
            base = "same worker evidence" if duplicate_output else f"worker {index} independent evidence"
            content = "\n".join([
                f"workerId: {assignment['workerId']}",
                f"taskId: {assignment['taskId']}",
                f"sessionId: {session_id}",
                f"dispatchContractSha256: {assignment['dispatchContractSha256']}",
                f"scope: {assignment['scopeIds'][0]}",
                *(f"reviewOf: {value}" for value in review),
                (base + " ") * 10,
            ])
            evidence.write_text(content, encoding="utf-8")
            write_json(receipt, {
                "schemaVersion": "3.2", "stage": "intake",
                "workerId": assignment["workerId"], "taskId": assignment["taskId"],
                "sessionId": session_id, "delegationMode": "native-agents",
                "invocation": invocation,
                "dispatchContractSha256": assignment["dispatchContractSha256"],
                "sessionEvidencePath": session_evidence.as_posix(),
                "sessionEvidenceSha256": session_evidence_sha,
                "issuedAt": f"2026-07-24T00:00:{index:02d}Z",
            })
            record_subagent_result(
                self.run,
                stage="intake",
                worker_id=assignment["workerId"],
                task_id=assignment["taskId"],
                session_id=session_id,
                invocation=invocation,
                invocation_receipt_file=receipt,
                session_evidence_file=session_evidence,
                evidence_file=evidence,
                review_of_worker_ids=review,
            )
            worker_ids.append(assignment["workerId"])
        lead_contract = self.run / "orchestration" / "intake" / "lead-contract.json"
        lead_contract_sha = sha256_file(lead_contract)
        aggregation = self.run / "orchestration" / "intake" / "lead-aggregation.md"
        aggregation.write_text("\n".join([
            "leadAgentId: INTAKE-LEAD",
            "leadSessionId: LEAD-SESSION-1",
            f"planFingerprint: {plan['planFingerprint']}",
            f"leadContractSha256: {lead_contract_sha}",
            *(f"acceptedWorkerId: {worker_id}" for worker_id in worker_ids),
            "lead merged all independent worker results, removed duplicates, resolved conflicts, and verified full scope coverage. " * 5,
        ]), encoding="utf-8")
        lead_session_evidence = self._write_codex_session("LEAD-SESSION-1", "intake", "lead")
        record_lead_aggregation(
            self.run,
            stage="intake",
            lead_agent_id="INTAKE-LEAD",
            lead_session_id="LEAD-SESSION-1",
            session_evidence_file=lead_session_evidence,
            evidence_file=aggregation,
            accepted_worker_ids=worker_ids,
            resolved_conflicts=["requirement wording overlap resolved"],
        )
        return plan

    def test_small_project_uses_minimum_two_subagents_not_fixed_sixty(self):
        count, signals, _ = recommended_subagent_count(self.run, self.state, "intake")
        self.assertEqual(count, MIN_SUBAGENTS)
        self.assertLess(count, MAX_SUBAGENTS)
        plan = ensure_agent_plan(self.run, self.state, "intake", force=True)
        self.assertFalse(plan["fixedSixty"])
        self.assertEqual(len(plan["assignments"]), 2)

    def test_large_project_scales_up_but_never_above_sixty(self):
        summary = read_json(self.run / "inventory" / "inventory-summary.json")
        summary.update({"fileCount": 100000, "directoryCount": 20000, "totalBytes": 10**12})
        write_json(self.run / "inventory" / "inventory-summary.json", summary)
        count, _, _ = recommended_subagent_count(self.run, self.state, "analyze")
        self.assertEqual(count, MAX_SUBAGENTS)

    def test_subagent_results_require_unique_independent_sessions(self):
        plan = ensure_agent_plan(self.run, self.state, "intake", force=True)
        first = plan["assignments"][0]
        second = plan["assignments"][1]
        same_session = "SAME-SESSION-01"

        def make_files(assignment, suffix, invocation):
            out = self.run / "orchestration" / "intake" / "outputs" / f"{suffix}.md"
            receipt = self.run / "orchestration" / "intake" / "receipts" / f"{suffix}.json"
            session_evidence = self._write_codex_session(same_session, assignment["taskId"], suffix)
            out.write_text("\n".join([
                assignment["workerId"], assignment["taskId"], same_session,
                assignment["dispatchContractSha256"], assignment["scopeIds"][0],
                *assignment["reviewTargetWorkerIds"], ("independent output " + suffix + " ") * 10,
            ]), encoding="utf-8")
            write_json(receipt, {
                "schemaVersion": "3.2", "stage": "intake", "workerId": assignment["workerId"],
                "taskId": assignment["taskId"], "sessionId": same_session,
                "delegationMode": "native-agents", "invocation": invocation,
                "dispatchContractSha256": assignment["dispatchContractSha256"],
                "sessionEvidencePath": session_evidence.as_posix(),
                "sessionEvidenceSha256": sha256_file(session_evidence),
                "issuedAt": "2026-07-24T00:00:00Z" if suffix == "one" else "2026-07-24T00:00:01Z",
            })
            return out, receipt, session_evidence

        one, receipt_one, session_one = make_files(first, "one", "/agents first")
        two, receipt_two, session_two = make_files(second, "two", "/agents second")
        record_subagent_result(
            self.run, stage="intake", worker_id=first["workerId"], task_id=first["taskId"],
            session_id=same_session, invocation="/agents first", invocation_receipt_file=receipt_one,
            session_evidence_file=session_one,
            evidence_file=one, review_of_worker_ids=first["reviewTargetWorkerIds"],
        )
        with self.assertRaises(ValueError):
            record_subagent_result(
                self.run, stage="intake", worker_id=second["workerId"], task_id=second["taskId"],
                session_id=same_session, invocation="/agents second", invocation_receipt_file=receipt_two,
                session_evidence_file=session_two,
                evidence_file=two, review_of_worker_ids=second["reviewTargetWorkerIds"],
            )

    def test_subagent_delegation_requires_native_agents(self):
        plan = ensure_agent_plan(self.run, self.state, "intake", force=True)
        assignment = plan["assignments"][0]
        with self.assertRaises(ValueError):
            record_subagent_result(
                self.run,
                stage="intake",
                worker_id=assignment["workerId"],
                task_id=assignment["taskId"],
                session_id="SUB-SESSION-NONNATIVE",
                invocation="independent task",
                invocation_receipt_file=self.run / "missing-receipt.json",
                session_evidence_file=self.run / "missing-session.jsonl",
                evidence_file=self.run / "missing-output.md",
                review_of_worker_ids=assignment["reviewTargetWorkerIds"],
                delegation_mode="independent-codex-task",
            )

    def test_complete_subagent_orchestration_has_no_agent_issues(self):
        self._complete_intake_agents()
        self.assertEqual(orchestration_issues(self.run, self.state, "intake"), [])

    def test_duplicate_subagent_outputs_are_rejected(self):
        self._complete_intake_agents()
        ledger_path = self.run / "orchestration" / "intake" / "execution-ledger.json"
        ledger = read_json(ledger_path)
        ledger["workers"][1]["evidenceSha256"] = ledger["workers"][0]["evidenceSha256"]
        write_json(ledger_path, ledger)
        codes = {item["code"] for item in orchestration_issues(self.run, self.state, "intake")}
        self.assertIn("SUBAGENT_OUTPUT_DUPLICATED", codes)

    def test_subagent_policy_tampering_is_rejected(self):
        ensure_agent_plan(self.run, self.state, "intake", force=True)
        policy_path = self.run / "contract" / "subagent-orchestration-policy.json"
        policy = read_json(policy_path)
        policy["minimumSubAgentsPerStage"] = 0
        write_json(policy_path, policy)
        codes = {item["code"] for item in orchestration_issues(self.run, self.state, "intake")}
        self.assertIn("SUBAGENT_POLICY_TAMPERED", codes)

    def test_missing_lead_aggregation_repair_preserves_worker_results(self):
        plan = self._complete_intake_agents()
        (self.run / "orchestration" / "intake" / "lead-aggregation.json").unlink()
        before = read_json(self.run / "orchestration" / "intake" / "execution-ledger.json")
        result = deterministic_repair(self.run, self.state, "intake", [{"code": "LEAD_AGENT_AGGREGATION_MISSING"}])
        after = read_json(self.run / "orchestration" / "intake" / "execution-ledger.json")
        self.assertEqual(len(before["workers"]), len(after["workers"]))
        action = next(item for item in result["actions"] if "subagent" in item.get("action", ""))
        self.assertTrue(action["preservedExistingWorkerResults"])

    def test_run_lock_enforces_subagent_bounds_and_prompt_only_ban(self):
        lock = read_json(self.run / "contract" / "run-lock.json")
        self.assertEqual(lock["subAgentMinimum"], 2)
        self.assertEqual(lock["subAgentMaximum"], 60)
        self.assertFalse(lock["fixedSixtySubAgents"])
        self.assertEqual(lock["promptOnlySubAgentDelegation"], "forbidden")

    def test_worker_dispatch_contracts_and_receipts_are_physical_and_unique(self):
        plan = self._complete_intake_agents()
        ledger = read_json(self.run / "orchestration" / "intake" / "execution-ledger.json")
        self.assertEqual(len(ledger["workers"]), plan["selectedSubAgents"])
        self.assertEqual(len({item["invocationReceiptSha256"] for item in ledger["workers"]}), plan["selectedSubAgents"])
        for assignment in plan["assignments"]:
            dispatch = self.run / assignment["dispatchContractPath"]
            self.assertTrue(dispatch.is_file())
            self.assertEqual(sha256_file(dispatch), assignment["dispatchContractSha256"])

    def test_every_worker_is_ring_cross_reviewed(self):
        plan = self._complete_intake_agents()
        ledger = read_json(self.run / "orchestration" / "intake" / "execution-ledger.json")
        reviewed = {target for item in ledger["workers"] for target in item["reviewOfWorkerIds"]}
        planned = {item["workerId"] for item in plan["assignments"]}
        self.assertEqual(reviewed, planned)
        self.assertEqual(orchestration_issues(self.run, self.state, "intake"), [])

    def test_lead_can_scale_above_floor_only_with_physical_justification(self):
        with self.assertRaises(ValueError):
            ensure_agent_plan(self.run, self.state, "intake", force=True, selected_count=3)
        reason = self.run / "orchestration" / "intake" / "lead-scale-reason.md"
        reason.parent.mkdir(parents=True, exist_ok=True)
        reason.write_text("\ud504\ub85c\uc81d\ud2b8\uc758 \ub3c5\ub9bd \uaddc\uc81c \uac80\ud1a0\uc640 \ucd94\uac00 \ub370\uc774\ud130 \uacbd\uacc4 \uac80\uc99d\uc774 \ud544\uc694\ud558\uc5ec worker \ud55c \uba85\uc744 \uc99d\uc6d0\ud569\ub2c8\ub2e4. " * 5, encoding="utf-8")
        plan = ensure_agent_plan(self.run, self.state, "intake", force=True, selected_count=3, justification_file=reason)
        self.assertEqual(plan["safetyFloorSubAgents"], 2)
        self.assertEqual(plan["selectedSubAgents"], 3)
        self.assertTrue(plan["leadScaleOverride"])

    def test_dispatch_or_receipt_tampering_is_rejected(self):
        self._complete_intake_agents()
        plan = read_json(self.run / "orchestration" / "intake" / "agent-plan.json")
        dispatch = self.run / plan["assignments"][0]["dispatchContractPath"]
        payload = read_json(dispatch)
        payload["role"] = "tampered-role"
        write_json(dispatch, payload)
        codes = {item["code"] for item in orchestration_issues(self.run, self.state, "intake")}
        self.assertIn("SUBAGENT_DISPATCH_CONTRACT_INVALID", codes)

    def test_distribution_completeness_validator_rejects_missing_engine_files(self):
        marketplace_root = PLUGIN_ROOT.parents[1]
        self.assertEqual(validate_distribution(PLUGIN_ROOT, marketplace_root), [])
        target = PLUGIN_ROOT / "scripts" / "kh_aw" / "orchestration.py"
        backup = target.read_bytes()
        target.unlink()
        try:
            errors = validate_distribution(PLUGIN_ROOT, marketplace_root)
            self.assertTrue(any("orchestration.py" in item for item in errors))
        finally:
            target.write_bytes(backup)

    def test_distribution_validator_rejects_stale_release_manifest_hash(self):
        marketplace_root = PLUGIN_ROOT.parents[1]
        target = marketplace_root / "FINAL_VALIDATION_REPORT.md"
        backup = target.read_bytes()
        target.write_bytes(backup + b"\nmanifest tamper\n")
        try:
            errors = validate_distribution(PLUGIN_ROOT, marketplace_root)
            self.assertTrue(any("release manifest hash/size mismatch" in item for item in errors))
        finally:
            target.write_bytes(backup)

    def test_versioned_cache_folder_is_a_valid_plugin_root(self):
        cache_root = self.temp / "cache" / "kh-aw" / "4.0.0"
        shutil.copytree(PLUGIN_ROOT, cache_root)
        self.assertFalse(any("folder name" in item for item in validate_plugin(cache_root)))

    def test_manifest_accepts_declared_lf_content_after_crlf_checkout(self):
        package = self.temp / "line-endings"
        (package / ".codex-plugin").mkdir(parents=True)
        (package / ".codex-plugin" / "plugin.json").write_text(
            '{"name":"kh-aw","version":"4.0.0"}\n', encoding="utf-8", newline="\n"
        )
        sample = package / "sample.txt"
        sample.write_text("one\ntwo\n", encoding="utf-8", newline="\n")
        build_package_manifest(package)
        sample.write_bytes(b"one\r\ntwo\r\n")
        self.assertEqual(validate_package_manifest(package), [])

    def test_plugin_target_is_inferred_from_manifest_instruction(self):
        inferred = infer_target_pipeline("Redesign this Codex plugin and plugin.json")
        self.assertEqual(inferred["targetPipeline"], "codex-plugin")

    def test_requirement_compiler_preserves_and_classifies_every_line(self):
        result = compile_requirements("Do not skip tests.\nCache evidence is required.\n")
        self.assertEqual(result["rawInstructionCount"], 2)
        self.assertEqual(result["rawInstructionCoverage"][0]["sourceText"], "Do not skip tests.")
        self.assertIn("prohibition", result["requirements"][0]["classifications"])
        self.assertIn("installation", result["requirements"][1]["classifications"])

    def test_task_graph_links_every_requirement(self):
        requirements = compile_requirements("First\nSecond\nThird")
        graph = build_task_graph(requirements)
        self.assertEqual(len(graph["tickets"]), 3)
        self.assertEqual(graph["tickets"][1]["dependencies"], ["TICKET-0001"])
        self.assertEqual(requirements["requirements"][2]["implementationTickets"], ["TICKET-0003"])

    def test_resume_keeps_repair_history_and_selects_first_incomplete_stage(self):
        self.state["stageStatus"]["intake"] = "passed"
        self.state["repair"]["signatures"]["abc"] = {"attempt": 2}
        save_state(self.run, self.state)
        result = resume_run(self.run)
        self.assertEqual(result["resume"]["stage"], "analyze")
        self.assertEqual(result["state"]["repair"]["signatures"]["abc"]["attempt"], 2)

    def test_deterministic_zip_rebuild_has_same_hash(self):
        first = build_deterministic_zip(PLUGIN_ROOT, self.temp / "one.zip")
        second = build_deterministic_zip(PLUGIN_ROOT, self.temp / "two.zip")
        self.assertEqual(first["sha256"], second["sha256"])

    def test_installation_inventory_detects_duplicate_version_roots(self):
        home = self.temp / "codex-home"
        for marketplace in ("one", "two"):
            target = home / "plugins" / "cache" / marketplace / "kh-aw" / "4.0.0"
            (target / ".codex-plugin").mkdir(parents=True)
            shutil.copy2(PLUGIN_ROOT / ".codex-plugin" / "plugin.json", target / ".codex-plugin" / "plugin.json")
        result = inspect_installations(home=home)
        self.assertTrue(result["shadowingRisk"])
        self.assertEqual(len(result["duplicates"]), 1)

    def test_skill_visibility_has_one_public_entrypoint(self):
        result = skill_visibility(PLUGIN_ROOT)
        self.assertTrue(result["singleEntrypoint"])
        self.assertEqual([item["name"] for item in result["visibleSkills"]], ["kh-aw"])


if __name__ == "__main__":
    unittest.main()
