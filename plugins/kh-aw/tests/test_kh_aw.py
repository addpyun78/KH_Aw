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
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from kh_aw.capabilities import record_capability
from kh_aw.contracts import create_run_contracts
from kh_aw.evidence import register_source
from kh_aw.distribution import validate_distribution
from kh_aw.gates import run_gate
from kh_aw.inventory import build_inventory
from kh_aw.plugin_validate import validate_plugin
from kh_aw.orchestration import (
    MIN_SUBAGENTS, MAX_SUBAGENTS, ensure_agent_plan, recommended_subagent_count,
    record_subagent_result, record_lead_aggregation, orchestration_issues,
)
from kh_aw.protection import compare_snapshot, create_protected_snapshot, restore_snapshot
from kh_aw.repair import create_repair_ticket, deterministic_repair
from kh_aw.run_lock import verify_run_lock, write_run_lock
from kh_aw.tooling import canonical_required_tool_ids, command_forbidden, execute_tool, tool_policy
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
        self.instructions = "첫 번째 요구사항\n두 번째 요구사항\n"
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
            "id": "E1", "label": "동적 실제 주제", "category": category,
            "requirementIds": ["REQ-001", "REQ-002"], "webQueries": ["one query", "two query"],
            "githubQueries": ["one github", "two github"], "status": "ready",
        } for category in ["competitor", "feature", "design-system", "image", "font", "icon", "motion", "accessibility", "platform", "conversion"]]
        write_json(self.run / "evidence" / "research-plan.json", plan)
        body = self.temp / "body.html"
        body.write_text("<html><body>" + ("본문 연구 내용 " * 100) + "</body></html>", encoding="utf-8")
        register_source(self.run, element_id="E1", source_type="web", url="https://duckduckgo.com/html/?q=test", body_file=body, project_fit_reason="현재 프로젝트 요구와 화면 구조를 비교하기 위한 구체적 근거입니다.")
        gate = run_gate(self.run, self.state, "research")
        self.assertIn("SEARCH_RESULT_IS_NOT_BODY_EVIDENCE", {item["code"] for item in gate["issues"]})

    def test_url_only_source_rejected(self):
        registry = {"schemaVersion": "2.0", "sources": [{
            "id": "SRC-1", "elementId": "E1", "sourceType": "web", "url": "https://example.com",
            "bodyPath": "missing.html", "textPath": "missing.txt", "bodySha256": "x", "httpStatus": 200,
            "extractedCharacters": 0, "projectFitReason": "현재 프로젝트에 매우 구체적으로 적합하다는 충분한 이유를 기록합니다.",
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

    def test_cli_advance_returns_zero_on_repair(self):
        completed = subprocess.run([sys.executable, str(SCRIPTS / "kh_aw_cli.py"), "advance", "--run-root", str(self.run), "--stage", "analyze"], capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0)
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
        record = record_capability(self.run, capability_id="codex-plan", mode="native", evidence_file=evidence, invocation="/plan", session_id="SESSION-1")
        self.assertEqual(record["mode"], "native")
        self.assertEqual(record["evidenceSha256"], sha256_file(evidence))

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
        report["accessibilityChecks"] = [{"pass": True, "evidence": "검사 완료"}]
        report["responsiveChecks"] = [{"pass": True, "evidence": "검사 완료"}]
        report["securityChecks"] = [{"pass": True, "evidence": "검사 완료"}]
        report["stateChecks"] = [{"pass": True, "evidence": "검사 완료"}]
        report["performanceChecks"] = [{"pass": True, "evidence": "검사 완료"}]
        report["visualRegressionChecks"] = [{"pass": True, "evidence": "검사 완료"}]
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
        record_lead_aggregation(
            self.run,
            stage="intake",
            lead_agent_id="INTAKE-LEAD",
            lead_session_id="LEAD-SESSION-1",
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
                "issuedAt": "2026-07-24T00:00:00Z" if suffix == "one" else "2026-07-24T00:00:01Z",
            })
            return out, receipt

        one, receipt_one = make_files(first, "one", "/agents first")
        two, receipt_two = make_files(second, "two", "/agents second")
        record_subagent_result(
            self.run, stage="intake", worker_id=first["workerId"], task_id=first["taskId"],
            session_id=same_session, invocation="/agents first", invocation_receipt_file=receipt_one,
            evidence_file=one, review_of_worker_ids=first["reviewTargetWorkerIds"],
        )
        with self.assertRaises(ValueError):
            record_subagent_result(
                self.run, stage="intake", worker_id=second["workerId"], task_id=second["taskId"],
                session_id=same_session, invocation="/agents second", invocation_receipt_file=receipt_two,
                evidence_file=two, review_of_worker_ids=second["reviewTargetWorkerIds"],
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
        reason.write_text("프로젝트의 독립 규제 검토와 추가 데이터 경계 검증이 필요하여 worker 한 명을 증원합니다. " * 5, encoding="utf-8")
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


if __name__ == "__main__":
    unittest.main()
