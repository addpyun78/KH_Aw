# 1차 소스 파일별 정밀 조사

대상: 62개 first-party 핵심 텍스트 파일. 각 항목의 전체 내용은 원본 ZIP에 있고, 본 문서는 해시·역할·의존·위험 신호·처리 결정을 연결합니다.

## 1. `.agents/skills/gpt-tasteskill/SKILL.md`

- 크기/줄: 7,857 bytes / 74 lines
- SHA-256: `2e64c269953f2656c21bf5a0fa6b4568e82fe0c72b36e8f84758e090349966a5`
- 분류/결정: `LEGACY_DESIGN_SKILL` / `REPLACE`
- 의존: 직접 추출된 import 없음
- export: 명시 export 추출 없음
- 위험 신호: `fixed-design-prescription`
- 처리 근거: Fixed fonts, layouts, images, or style rules are replaced with project-specific research and every-page design evidence.

## 2. `.agents/skills/taste-skill/SKILL.md`

- 크기/줄: 87,253 bytes / 1206 lines
- SHA-256: `aa194351b246b8b4799099d4ed7b033d29eab6e6e3d58d8d2172978be7b3ec89`
- 분류/결정: `LEGACY_DESIGN_SKILL` / `REPLACE`
- 의존: `gsap`, `gsap/ScrollTrigger`, `motion/react`, `react`
- export: `HorizontalPan`, `RevealStagger`, `StickyStack`
- 위험 신호: `fixed-design-prescription`, `large-module`
- 처리 근거: Fixed fonts, layouts, images, or style rules are replaced with project-specific research and every-page design evidence.

## 3. `backend/agy-bridge.mjs`

- 크기/줄: 86,581 bytes / 1971 lines
- SHA-256: `3e9d9782c234017d37a742de14e7ba96b25659774b3ac1b7c3d09d06c2480308`
- 분류/결정: `LEGACY_BACKEND_CORE` / `REENGINEER`
- 의존: `../shared/constants.mjs`, `../shared/logger.mjs`, `./production-contract.mjs`, `./tasklist-protocol.mjs`, `./token-limit.mjs`, `node:child_process`, `node:crypto`, `node:events`, `node:fs`, `node:path`, `node:url`
- export: `AgyBridge`, `async`, `bindTasklistRecordToRuntime`, `extractCodexSessionAssistantText`, `extractCompletedActorProof`, `isCodexSessionNativeGoalCompleteCall`, `isCodexSessionTaskComplete`
- 위험 신호: `local-model/cache-coupling`, `process-execution`, `silent-empty-catch`, `large-module`
- 처리 근거: Behavior is mapped into a web-compatible plugin state machine, evidence gates, protected analysis mode, and nonterminal repair loop.

## 4. `backend/ai-providers.mjs`

- 크기/줄: 6,297 bytes / 195 lines
- SHA-256: `bfd8fddb55c61ffa4a20e6c81b5348c22eb1ec98cc05c730e3fab4d92301beda`
- 분류/결정: `LEGACY_BACKEND_CORE` / `REENGINEER`
- 의존: `node:child_process`, `node:fs/promises`, `node:os`, `node:path`
- export: `AI_PROVIDERS`, `async`, `modelFamilyFor`, `normalizeProviderId`
- 위험 신호: `local-model/cache-coupling`, `process-execution`
- 처리 근거: Behavior is mapped into a web-compatible plugin state machine, evidence gates, protected analysis mode, and nonterminal repair loop.

## 5. `backend/artifact-guard.mjs`

- 크기/줄: 5,098 bytes / 174 lines
- SHA-256: `5ee7b4fedb920c8eeec359363e3e5cc9a47080df9549e60831e194b454a4d70f`
- 분류/결정: `LEGACY_BACKEND_CORE` / `REENGINEER`
- 의존: `../shared/constants.mjs`, `../shared/file-utils.mjs`, `../shared/logger.mjs`, `node:fs`, `node:path`
- export: `async`, `default`
- 위험 신호: 정적 패턴 기준 특이 신호 없음
- 처리 근거: Behavior is mapped into a web-compatible plugin state machine, evidence gates, protected analysis mode, and nonterminal repair loop.

## 6. `backend/artifact-writer.mjs`

- 크기/줄: 8,777 bytes / 255 lines
- SHA-256: `c7f5a8fcedd2e22286a8b6e2c958947a863e9d12218267c00f46bbd780860dda`
- 분류/결정: `LEGACY_BACKEND_CORE` / `REENGINEER`
- 의존: `../shared/file-utils.mjs`, `../shared/logger.mjs`, `./production-validator.mjs`, `node:fs`, `node:path`
- export: `async`, `default`
- 위험 신호: `process-execution`
- 처리 근거: Behavior is mapped into a web-compatible plugin state machine, evidence gates, protected analysis mode, and nonterminal repair loop.

## 7. `backend/auto-repair.mjs`

- 크기/줄: 97,788 bytes / 2607 lines
- SHA-256: `b0152cbfc2b2932e800863898e3266a521527e4f42903ce41472b378e8131511`
- 분류/결정: `LEGACY_BACKEND_CORE` / `REENGINEER`
- 의존: `../shared/file-utils.mjs`, `../shared/logger.mjs`, `../shared/path-utils.mjs`, `./agy-bridge.mjs`, `node:child_process`, `node:crypto`, `node:fs`, `node:path`, `node:url`
- export: `AutoRepairManager`, `__test`, `async`
- 위험 신호: `manual-design-selection`, `process-execution`, `large-module`
- 처리 근거: Behavior is mapped into a web-compatible plugin state machine, evidence gates, protected analysis mode, and nonterminal repair loop.

## 8. `backend/file-handler.mjs`

- 크기/줄: 7,098 bytes / 237 lines
- SHA-256: `98d5553e5113d768434d1571d5f29a620f9e227321a245577ed722ecfc167a50`
- 분류/결정: `LEGACY_BACKEND_CORE` / `REENGINEER`
- 의존: `../shared/constants.mjs`, `../shared/file-utils.mjs`, `../shared/logger.mjs`, `multer`, `node:path`, `node:url`, `uuid`
- export: `createUploadMiddleware`, `default`, `processUploadedFiles`, `uploadErrorHandler`, `uploadMiddleware`
- 위험 신호: 정적 패턴 기준 특이 신호 없음
- 처리 근거: Behavior is mapped into a web-compatible plugin state machine, evidence gates, protected analysis mode, and nonterminal repair loop.

## 9. `backend/pipeline.mjs`

- 크기/줄: 135,387 bytes / 3501 lines
- SHA-256: `dde879176b3e174f3286144ddcb839d1a9a422a491474697678d9646eef4977c`
- 분류/결정: `LEGACY_BACKEND_CORE` / `REENGINEER`
- 의존: `../shared/constants.mjs`, `../shared/file-utils.mjs`, `../shared/logger.mjs`, `../shared/path-utils.mjs`, `./agy-bridge.mjs`, `./ai-providers.mjs`, `./artifact-guard.mjs`, `./artifact-writer.mjs`, `./auto-repair.mjs`, `./production-validator.mjs`, `./project-manager.mjs`, `./runtime-resource-loader.mjs`, `./stage-tasklist.mjs`, `./state-recovery.mjs`, `./tasklist-protocol.mjs`, `./taste-skill.mjs`, `./token-limit.mjs`, `./web-research.mjs`, `node:crypto`, `node:events`, `node:fs`, `node:path`
- export: `async`, `pipeline`
- 위험 신호: `manual-design-selection`, `local-model/cache-coupling`, `large-module`
- 처리 근거: Behavior is mapped into a web-compatible plugin state machine, evidence gates, protected analysis mode, and nonterminal repair loop.

## 10. `backend/production-contract.mjs`

- 크기/줄: 29,939 bytes / 244 lines
- SHA-256: `e5ce3062597258bcf6d85a59107f15831f6db1b4f6413d35df162a0bffcd6f05`
- 분류/결정: `LEGACY_BACKEND_CORE` / `REENGINEER`
- 의존: 직접 추출된 import 없음
- export: `buildProductionContract`
- 위험 신호: `manual-design-selection`, `local-model/cache-coupling`
- 처리 근거: Behavior is mapped into a web-compatible plugin state machine, evidence gates, protected analysis mode, and nonterminal repair loop.

## 11. `backend/production-validator.mjs`

- 크기/줄: 122,363 bytes / 2617 lines
- SHA-256: `852864786ac563c65095b67c7ca6581e1a2afb18d0f464f5440c6d770179e9a3`
- 분류/결정: `LEGACY_BACKEND_CORE` / `REENGINEER`
- 의존: `../shared/path-utils.mjs`, `./production-contract.mjs`, `node:fs`, `node:path`
- export: `async`, `createSkippedProductionOutputGate`, `ensureStagePolicyData`, `iconPolicyIsDynamic`, `inspectStageTaskList`, `shouldRunProductionOutputGate`, `validateIconEntryList`, `validateStagePolicyResult`
- 위험 신호: `manual-design-selection`, `local-model/cache-coupling`, `process-execution`, `large-module`
- 처리 근거: Behavior is mapped into a web-compatible plugin state machine, evidence gates, protected analysis mode, and nonterminal repair loop.

## 12. `backend/project-manager.mjs`

- 크기/줄: 34,636 bytes / 942 lines
- SHA-256: `b58a2565e1de257bbd5c8d630dfce19f36506adc01531d7bed0243d9dc34436e`
- 분류/결정: `LEGACY_BACKEND_CORE` / `REENGINEER`
- 의존: `../shared/constants.mjs`, `../shared/file-utils.mjs`, `../shared/logger.mjs`, `../shared/path-utils.mjs`, `./auto-repair.mjs`, `./production-validator.mjs`, `./state-recovery.mjs`, `node:path`, `node:url`, `uuid`
- export: `projectManager`
- 위험 신호: `local-model/cache-coupling`
- 처리 근거: Behavior is mapped into a web-compatible plugin state machine, evidence gates, protected analysis mode, and nonterminal repair loop.

## 13. `backend/runtime-resource-loader.mjs`

- 크기/줄: 3,038 bytes / 92 lines
- SHA-256: `cb0c5559cdda7fb2575aafca1cc7d45881411d0f2da640301932ffc025c4b38b`
- 분류/결정: `LEGACY_BACKEND_CORE` / `REENGINEER`
- 의존: `node:fs`, `node:path`
- export: `async`, `default`
- 위험 신호: 정적 패턴 기준 특이 신호 없음
- 처리 근거: Behavior is mapped into a web-compatible plugin state machine, evidence gates, protected analysis mode, and nonterminal repair loop.

## 14. `backend/server.mjs`

- 크기/줄: 19,000 bytes / 572 lines
- SHA-256: `236feda30c5fc203ed4f45cfeab6cd591477043ee209990ae35c70e5f72aae24`
- 분류/결정: `LEGACY_BACKEND_CORE` / `REENGINEER`
- 의존: `../shared/constants.mjs`, `../shared/file-utils.mjs`, `../shared/logger.mjs`, `./ai-providers.mjs`, `./file-handler.mjs`, `./pipeline.mjs`, `./project-manager.mjs`, `./state-recovery.mjs`, `cors`, `dotenv`, `express`, `node:child_process`, `node:fs`, `node:http`, `node:path`, `node:url`, `node:util`, `ws`
- export: 명시 export 추출 없음
- 위험 신호: `local-model/cache-coupling`, `process-execution`, `silent-empty-catch`
- 처리 근거: Behavior is mapped into a web-compatible plugin state machine, evidence gates, protected analysis mode, and nonterminal repair loop.

## 15. `backend/stage-tasklist.mjs`

- 크기/줄: 12,276 bytes / 209 lines
- SHA-256: `d64f6c38101db6bf1a069dd8f53ffd2e0592e303a927a3505674861cef2aa73b`
- 분류/결정: `LEGACY_BACKEND_CORE` / `REENGINEER`
- 의존: 직접 추출된 import 없음
- export: `completeStageTaskList`, `createStageTaskList`, `failStageTaskList`, `formatTaskListForPrompt`
- 위험 신호: 정적 패턴 기준 특이 신호 없음
- 처리 근거: Behavior is mapped into a web-compatible plugin state machine, evidence gates, protected analysis mode, and nonterminal repair loop.

## 16. `backend/state-recovery.mjs`

- 크기/줄: 21,545 bytes / 604 lines
- SHA-256: `745d31c5028873f1455907740ea1b8fdc12a755fc6414bc8b779bc418363d5f6`
- 분류/결정: `LEGACY_BACKEND_CORE` / `REENGINEER`
- 의존: `../shared/constants.mjs`, `../shared/file-utils.mjs`, `../shared/logger.mjs`, `node:fs`, `node:path`, `node:url`
- export: `stateRecovery`
- 위험 신호: 정적 패턴 기준 특이 신호 없음
- 처리 근거: Behavior is mapped into a web-compatible plugin state machine, evidence gates, protected analysis mode, and nonterminal repair loop.

## 17. `backend/tasklist-protocol.mjs`

- 크기/줄: 26,055 bytes / 550 lines
- SHA-256: `9226ae3356f4b37422233b8b0615d41d8d22930632e01a52221bd88b62fa912f`
- 분류/결정: `LEGACY_BACKEND_CORE` / `REENGINEER`
- 의존: 직접 추출된 import 없음
- export: `TASKLIST_EVENTS`, `TASKLIST_MARKER`, `TasklistStreamParser`, `applyTasklistRecord`, `buildTasklistContinuationContract`, `buildTasklistPromptContract`, `normalizeTasklistRecord`, `summarizeTasklist`
- 위험 신호: `local-model/cache-coupling`
- 처리 근거: Behavior is mapped into a web-compatible plugin state machine, evidence gates, protected analysis mode, and nonterminal repair loop.

## 18. `backend/taste-skill.mjs`

- 크기/줄: 1,502 bytes / 37 lines
- SHA-256: `f94840ea4f49d33b12e01d7e430b46713875f0074ddec57e0718a245bb4e7088`
- 분류/결정: `LEGACY_BACKEND_CORE` / `REENGINEER`
- 의존: `node:fs`, `node:path`
- export: `getTasteSkillGuidance`
- 위험 신호: 정적 패턴 기준 특이 신호 없음
- 처리 근거: Behavior is mapped into a web-compatible plugin state machine, evidence gates, protected analysis mode, and nonterminal repair loop.

## 19. `backend/token-limit.mjs`

- 크기/줄: 3,009 bytes / 75 lines
- SHA-256: `7f6ee4e61fa3fa30bcd68eba63d06d8a743e55977e131b1dd3bcf829400bb764`
- 분류/결정: `LEGACY_BACKEND_CORE` / `REENGINEER`
- 의존: 직접 추출된 import 없음
- export: `detectTokenLimit`
- 위험 신호: 정적 패턴 기준 특이 신호 없음
- 처리 근거: Behavior is mapped into a web-compatible plugin state machine, evidence gates, protected analysis mode, and nonterminal repair loop.

## 20. `backend/web-research.mjs`

- 크기/줄: 21,466 bytes / 587 lines
- SHA-256: `334e72aa6ef1ae27b07ce497da19c3ffaa5c662d4652f7ae20d10dd705c1b565`
- 분류/결정: `LEGACY_BACKEND_CORE` / `REENGINEER`
- 의존: `../shared/file-utils.mjs`, `../shared/path-utils.mjs`, `node:fs`, `node:path`
- export: `async`, `default`, `deriveResearchElements`, `minimumSourcesForResearchElement`
- 위험 신호: `search-provider-coupling`, `silent-empty-catch`
- 처리 근거: Behavior is mapped into a web-compatible plugin state machine, evidence gates, protected analysis mode, and nonterminal repair loop.

## 21. `config/default.json`

- 크기/줄: 311 bytes / 15 lines
- SHA-256: `3de3ac56c11b8cd9354f8d5809530561a5c98c684febbe2184546c492e74f5a8`
- 분류/결정: `LEGACY_PROMPT_CONFIG` / `REPLACE`
- 의존: 직접 추출된 import 없음
- export: 명시 export 추출 없음
- 위험 신호: `local-model/cache-coupling`
- 처리 근거: Prompt-heavy contracts are replaced by JSON artifacts and executable validators.

## 22. `config/stages.json`

- 크기/줄: 21,882 bytes / 132 lines
- SHA-256: `7aeebc1ae2ac1078d295f85ae942d2ed744fbdeffd81ce8c8960253da185831f`
- 분류/결정: `LEGACY_PROMPT_CONFIG` / `REPLACE`
- 의존: 직접 추출된 import 없음
- export: 명시 export 추출 없음
- 위험 신호: `manual-design-selection`
- 처리 근거: Prompt-heavy contracts are replaced by JSON artifacts and executable validators.

## 23. `config/translations.json`

- 크기/줄: 4,803 bytes / 154 lines
- SHA-256: `b28892e7e8eb1650f269015e0db6028b301c22879d6216cc2c870578515daef7`
- 분류/결정: `LEGACY_PROMPT_CONFIG` / `REPLACE`
- 의존: 직접 추출된 import 없음
- export: 명시 export 추출 없음
- 위험 신호: 정적 패턴 기준 특이 신호 없음
- 처리 근거: Prompt-heavy contracts are replaced by JSON artifacts and executable validators.

## 24. `frontend/components/progress-bar.mjs`

- 크기/줄: 6,502 bytes / 175 lines
- SHA-256: `572d5260d226b92716591456bdee5cd885b301495d91f6e0e6ddb98d2a543758`
- 분류/결정: `STANDALONE_LOCAL_UI` / `EXCLUDE_TARGET_MISMATCH`
- 의존: 직접 추출된 import 없음
- export: `ProgressBar`
- 위험 신호: 정적 패턴 기준 특이 신호 없음
- 처리 근거: Standalone Express/WebSocket UI is not needed for a Codex web marketplace skill-only plugin.

## 25. `frontend/components/spec-table.mjs`

- 크기/줄: 3,644 bytes / 111 lines
- SHA-256: `8fc8f5cd5cfc5ff8fffc24e8fd86f418fd610c7c63f9ecbf6341042a4c37ced6`
- 분류/결정: `STANDALONE_LOCAL_UI` / `EXCLUDE_TARGET_MISMATCH`
- 의존: 직접 추출된 import 없음
- export: `SpecTable`
- 위험 신호: 정적 패턴 기준 특이 신호 없음
- 처리 근거: Standalone Express/WebSocket UI is not needed for a Codex web marketplace skill-only plugin.

## 26. `frontend/components/task-tree.mjs`

- 크기/줄: 9,878 bytes / 310 lines
- SHA-256: `8eeebe8eac71e78e3089b756014dd90d384e94f64529199d57125b4f952ed006`
- 분류/결정: `STANDALONE_LOCAL_UI` / `EXCLUDE_TARGET_MISMATCH`
- 의존: 직접 추출된 import 없음
- export: `TaskTree`
- 위험 신호: 정적 패턴 기준 특이 신호 없음
- 처리 근거: Standalone Express/WebSocket UI is not needed for a Codex web marketplace skill-only plugin.

## 27. `frontend/components/toast.mjs`

- 크기/줄: 3,874 bytes / 107 lines
- SHA-256: `7be2007f3e43342802f5a1f7df0b00d15165e9563d2de77a1c3f6ac9b0df4b9e`
- 분류/결정: `STANDALONE_LOCAL_UI` / `EXCLUDE_TARGET_MISMATCH`
- 의존: 직접 추출된 import 없음
- export: `Toast`, `toast`
- 위험 신호: 정적 패턴 기준 특이 신호 없음
- 처리 근거: Standalone Express/WebSocket UI is not needed for a Codex web marketplace skill-only plugin.

## 28. `frontend/css/animations.css`

- 크기/줄: 5,774 bytes / 324 lines
- SHA-256: `8b69f7bf1a33b588f366891e79ea62153da65dc5f219ddb8d2e1f1fd54cf872b`
- 분류/결정: `STANDALONE_LOCAL_UI` / `EXCLUDE_TARGET_MISMATCH`
- 의존: 직접 추출된 import 없음
- export: 명시 export 추출 없음
- 위험 신호: 정적 패턴 기준 특이 신호 없음
- 처리 근거: Standalone Express/WebSocket UI is not needed for a Codex web marketplace skill-only plugin.

## 29. `frontend/css/concept-picker.css`

- 크기/줄: 15,118 bytes / 738 lines
- SHA-256: `a1ff0c764939e3d22738f66f9703ccedb7b31ffc04a17a864425491f959ed948`
- 분류/결정: `MANUAL_DESIGN_UI` / `DELETE_REPLACED`
- 의존: 직접 추출된 import 없음
- export: 명시 export 추출 없음
- 위험 신호: `manual-design-selection`
- 처리 근거: Manual concept/color selection is removed and replaced with dynamic body-backed research gates.

## 30. `frontend/css/controls.css`

- 크기/줄: 17,998 bytes / 878 lines
- SHA-256: `8aa1b8d376793750378993da3efd8ecfe2eed1cf05e9848a0fc3ecda66d5ca82`
- 분류/결정: `STANDALONE_LOCAL_UI` / `EXCLUDE_TARGET_MISMATCH`
- 의존: 직접 추출된 import 없음
- export: 명시 export 추출 없음
- 위험 신호: `manual-design-selection`
- 처리 근거: Standalone Express/WebSocket UI is not needed for a Codex web marketplace skill-only plugin.

## 31. `frontend/css/main.css`

- 크기/줄: 5,183 bytes / 334 lines
- SHA-256: `999751e0903c561d2cbc8bd000fb72b99c9322556e8ba15fb7315878d81e0e42`
- 분류/결정: `STANDALONE_LOCAL_UI` / `EXCLUDE_TARGET_MISMATCH`
- 의존: 직접 추출된 import 없음
- export: 명시 export 추출 없음
- 위험 신호: 정적 패턴 기준 특이 신호 없음
- 처리 근거: Standalone Express/WebSocket UI is not needed for a Codex web marketplace skill-only plugin.

## 32. `frontend/css/monitor.css`

- 크기/줄: 4,839 bytes / 223 lines
- SHA-256: `4edb832dc8908e6cad7a1130b562986d18c4ad6a68877eba0c7ce74be14e6882`
- 분류/결정: `STANDALONE_LOCAL_UI` / `EXCLUDE_TARGET_MISMATCH`
- 의존: 직접 추출된 import 없음
- export: 명시 export 추출 없음
- 위험 신호: 정적 패턴 기준 특이 신호 없음
- 처리 근거: Standalone Express/WebSocket UI is not needed for a Codex web marketplace skill-only plugin.

## 33. `frontend/css/panels.css`

- 크기/줄: 8,588 bytes / 408 lines
- SHA-256: `cc3d4c96daaf28905e6bf4ba3ff3d58b926fc291418d2eec9c6b6811b09b4be2`
- 분류/결정: `STANDALONE_LOCAL_UI` / `EXCLUDE_TARGET_MISMATCH`
- 의존: 직접 추출된 import 없음
- export: 명시 export 추출 없음
- 위험 신호: 정적 패턴 기준 특이 신호 없음
- 처리 근거: Standalone Express/WebSocket UI is not needed for a Codex web marketplace skill-only plugin.

## 34. `frontend/css/plan-view.css`

- 크기/줄: 12,796 bytes / 615 lines
- SHA-256: `21db915d9cd4e2877fff86c2b83d029d0615dd4342b0b4ffb916d58e496749b6`
- 분류/결정: `STANDALONE_LOCAL_UI` / `EXCLUDE_TARGET_MISMATCH`
- 의존: 직접 추출된 import 없음
- export: 명시 export 추출 없음
- 위험 신호: 정적 패턴 기준 특이 신호 없음
- 처리 근거: Standalone Express/WebSocket UI is not needed for a Codex web marketplace skill-only plugin.

## 35. `frontend/index.html`

- 크기/줄: 12,145 bytes / 256 lines
- SHA-256: `7874f977b4e1eb9ca57425771860caf4fa271b444a1d005edc4e344e5d373fb8`
- 분류/결정: `STANDALONE_LOCAL_UI` / `EXCLUDE_TARGET_MISMATCH`
- 의존: 직접 추출된 import 없음
- export: 명시 export 추출 없음
- 위험 신호: `manual-design-selection`
- 처리 근거: Standalone Express/WebSocket UI is not needed for a Codex web marketplace skill-only plugin.

## 36. `frontend/js/app.mjs`

- 크기/줄: 45,771 bytes / 1206 lines
- SHA-256: `b87a31fba06aea8d911acef2a1849254db289c85858a06d8dc4a63756325caf7`
- 분류/결정: `STANDALONE_LOCAL_UI` / `EXCLUDE_TARGET_MISMATCH`
- 의존: `../components/progress-bar.mjs`, `../components/spec-table.mjs`, `../components/task-tree.mjs`, `../components/toast.mjs`, `./color-picker.mjs`, `./concept-picker.mjs`, `./file-drop.mjs`, `./mode-toggle.mjs`, `./natural-lang.mjs`, `./pipeline-view.mjs`, `./plan-presenter.mjs`, `./project-manager.mjs`, `./ws-client.mjs`
- export: 명시 export 추출 없음
- 위험 신호: `manual-design-selection`, `local-model/cache-coupling`, `large-module`
- 처리 근거: Standalone Express/WebSocket UI is not needed for a Codex web marketplace skill-only plugin.

## 37. `frontend/js/color-picker.mjs`

- 크기/줄: 21,876 bytes / 470 lines
- SHA-256: `881f57a64c67d6c6e21f9780bfa41415bda0c6863516d41ef237a94140ac3ad8`
- 분류/결정: `MANUAL_DESIGN_UI` / `DELETE_REPLACED`
- 의존: 직접 추출된 import 없음
- export: `ColorPicker`
- 위험 신호: 정적 패턴 기준 특이 신호 없음
- 처리 근거: Manual concept/color selection is removed and replaced with dynamic body-backed research gates.

## 38. `frontend/js/concept-picker.mjs`

- 크기/줄: 12,957 bytes / 364 lines
- SHA-256: `ca148ddfef3dc8f106c701f93f5ab335ea4b15e5e327a776a273fa21b36b124a`
- 분류/결정: `MANUAL_DESIGN_UI` / `DELETE_REPLACED`
- 의존: 직접 추출된 import 없음
- export: `ConceptPicker`
- 위험 신호: `manual-design-selection`
- 처리 근거: Manual concept/color selection is removed and replaced with dynamic body-backed research gates.

## 39. `frontend/js/file-drop.mjs`

- 크기/줄: 10,971 bytes / 402 lines
- SHA-256: `91203225eb15699041f2fefb64c93558feac25ee7e39f19e05153aafb4a357d5`
- 분류/결정: `STANDALONE_LOCAL_UI` / `EXCLUDE_TARGET_MISMATCH`
- 의존: 직접 추출된 import 없음
- export: `FileDrop`
- 위험 신호: 정적 패턴 기준 특이 신호 없음
- 처리 근거: Standalone Express/WebSocket UI is not needed for a Codex web marketplace skill-only plugin.

## 40. `frontend/js/mode-toggle.mjs`

- 크기/줄: 2,474 bytes / 85 lines
- SHA-256: `d11c72d5f242d934a4bdf4ad1eff57d7fa356ce990f79b59f518498c575c403d`
- 분류/결정: `STANDALONE_LOCAL_UI` / `EXCLUDE_TARGET_MISMATCH`
- 의존: 직접 추출된 import 없음
- export: `ModeToggle`
- 위험 신호: 정적 패턴 기준 특이 신호 없음
- 처리 근거: Standalone Express/WebSocket UI is not needed for a Codex web marketplace skill-only plugin.

## 41. `frontend/js/natural-lang.mjs`

- 크기/줄: 5,581 bytes / 189 lines
- SHA-256: `dcc354a5ade59ba7490d512e4d70c043424ef6535999cf9566b5b6132c22a651`
- 분류/결정: `STANDALONE_LOCAL_UI` / `EXCLUDE_TARGET_MISMATCH`
- 의존: 직접 추출된 import 없음
- export: `NaturalLanguageEngine`
- 위험 신호: 정적 패턴 기준 특이 신호 없음
- 처리 근거: Standalone Express/WebSocket UI is not needed for a Codex web marketplace skill-only plugin.

## 42. `frontend/js/node-graph.mjs`

- 크기/줄: 8,483 bytes / 275 lines
- SHA-256: `eb7ec7897fd05a81303273acd7c9265f6351ed53119eb9e354e6c90ae8453d54`
- 분류/결정: `STANDALONE_LOCAL_UI` / `EXCLUDE_TARGET_MISMATCH`
- 의존: 직접 추출된 import 없음
- export: `NodeGraph`
- 위험 신호: 정적 패턴 기준 특이 신호 없음
- 처리 근거: Standalone Express/WebSocket UI is not needed for a Codex web marketplace skill-only plugin.

## 43. `frontend/js/pipeline-view.mjs`

- 크기/줄: 5,732 bytes / 180 lines
- SHA-256: `2ef91eff78b2f847fcffbeb6b7e32176e830234b68468a30174e0fd9081d6221`
- 분류/결정: `STANDALONE_LOCAL_UI` / `EXCLUDE_TARGET_MISMATCH`
- 의존: 직접 추출된 import 없음
- export: `PipelineView`
- 위험 신호: 정적 패턴 기준 특이 신호 없음
- 처리 근거: Standalone Express/WebSocket UI is not needed for a Codex web marketplace skill-only plugin.

## 44. `frontend/js/plan-presenter.mjs`

- 크기/줄: 8,714 bytes / 291 lines
- SHA-256: `6ddaf90290da141cfecaf8a90e5fa2c9a39070f6877e50d1c5477537446b5fa1`
- 분류/결정: `STANDALONE_LOCAL_UI` / `EXCLUDE_TARGET_MISMATCH`
- 의존: `../components/spec-table.mjs`, `./node-graph.mjs`, `./radar-chart.mjs`
- export: `PlanPresenter`
- 위험 신호: 정적 패턴 기준 특이 신호 없음
- 처리 근거: Standalone Express/WebSocket UI is not needed for a Codex web marketplace skill-only plugin.

## 45. `frontend/js/project-manager.mjs`

- 크기/줄: 8,777 bytes / 358 lines
- SHA-256: `f85752fd695ef5d16380697144d7b727a50ed9f40a6cb0ec88704525575ae711`
- 분류/결정: `STANDALONE_LOCAL_UI` / `EXCLUDE_TARGET_MISMATCH`
- 의존: 직접 추출된 import 없음
- export: `ProjectManagerUI`
- 위험 신호: 정적 패턴 기준 특이 신호 없음
- 처리 근거: Standalone Express/WebSocket UI is not needed for a Codex web marketplace skill-only plugin.

## 46. `frontend/js/radar-chart.mjs`

- 크기/줄: 8,129 bytes / 310 lines
- SHA-256: `b1f0565233ff27315a57762bb46b63339cfa8082601670369c3c68a34e414807`
- 분류/결정: `STANDALONE_LOCAL_UI` / `EXCLUDE_TARGET_MISMATCH`
- 의존: 직접 추출된 import 없음
- export: `RadarChart`
- 위험 신호: 정적 패턴 기준 특이 신호 없음
- 처리 근거: Standalone Express/WebSocket UI is not needed for a Codex web marketplace skill-only plugin.

## 47. `frontend/js/ws-client.mjs`

- 크기/줄: 5,268 bytes / 217 lines
- SHA-256: `5202351fd5f2c2f384415ac92df1b7faff897b403c9e73d7f2634f18fafcb860`
- 분류/결정: `STANDALONE_LOCAL_UI` / `EXCLUDE_TARGET_MISMATCH`
- 의존: 직접 추출된 import 없음
- export: `WSClient`
- 위험 신호: 정적 패턴 기준 특이 신호 없음
- 처리 근거: Standalone Express/WebSocket UI is not needed for a Codex web marketplace skill-only plugin.

## 48. `shared/constants.mjs`

- 크기/줄: 6,555 bytes / 236 lines
- SHA-256: `bef28d888c1881fd842c78b0ead1f4e3699086783cbe4d3191856d44fab4e105`
- 분류/결정: `LEGACY_SHARED_CORE` / `REENGINEER`
- 의존: 직접 추출된 import 없음
- export: `CASES`, `COLORS`, `DEFAULTS`, `FILE_EXTENSIONS`, `MODES`, `STAGES`, `STAGE_BY_ID`, `STAGE_BY_KEY`, `STAGE_MODELS`, `STAGE_ORDER`, `STAGE_STATUS_MAP`, `STATUS_CODES`, `WS_EVENTS`
- 위험 신호: `local-model/cache-coupling`
- 처리 근거: Path/file/hash utilities are reimplemented in the plugin with workspace containment and atomic writes.

## 49. `shared/file-utils.mjs`

- 크기/줄: 14,760 bytes / 475 lines
- SHA-256: `395fce6fb62794d5dbcf1162aacbdb61f6172c0eb2ee6b42943f0d44b7ecbf28`
- 분류/결정: `LEGACY_SHARED_CORE` / `REENGINEER`
- 의존: `./constants.mjs`, `node:fs`, `node:path`
- export: `JsonReadError`, `async`, `isDocumentFile`, `isImageFile`, `isVideoFile`
- 위험 신호: 정적 패턴 기준 특이 신호 없음
- 처리 근거: Path/file/hash utilities are reimplemented in the plugin with workspace containment and atomic writes.

## 50. `shared/logger.mjs`

- 크기/줄: 6,938 bytes / 276 lines
- SHA-256: `137118d2bd753c7782987891258808e87be46c3d82d25b12a7369c22fefbb212`
- 분류/결정: `LEGACY_SHARED_CORE` / `REENGINEER`
- 의존: `node:fs`, `node:path`, `node:url`
- export: `logger`, `translateToNaturalLanguage`
- 위험 신호: 정적 패턴 기준 특이 신호 없음
- 처리 근거: Path/file/hash utilities are reimplemented in the plugin with workspace containment and atomic writes.

## 51. `shared/path-utils.mjs`

- 크기/줄: 1,258 bytes / 41 lines
- SHA-256: `dfcf0985fa478f9f494cf9df0763c8b4c35c3a418a5e7eb4e7bf1d5a0207d0e1`
- 분류/결정: `LEGACY_SHARED_CORE` / `REENGINEER`
- 의존: `node:path`
- export: `isInsidePath`, `normalizeWorkspacePath`, `windowsPathToWslPath`
- 위험 신호: 정적 패턴 기준 특이 신호 없음
- 처리 근거: Path/file/hash utilities are reimplemented in the plugin with workspace containment and atomic writes.

## 52. `tests/codex-runtime-capabilities.test.mjs`

- 크기/줄: 8,545 bytes / 136 lines
- SHA-256: `5481f5fd76223a355ba76acc3991c92af6127f7cc1a951308e70dbddf1af7126`
- 분류/결정: `LEGACY_TEST` / `MAP_AND_REPLACE`
- 의존: `../backend/ai-providers.mjs`, `node:assert/strict`, `node:fs/promises`, `node:test`
- export: 명시 export 추출 없음
- 위험 신호: `local-model/cache-coupling`
- 처리 근거: Original behavior is audited; plugin-specific cross-platform tests replace CLI/local-cache assumptions.

## 53. `tests/codex-session-stream.test.mjs`

- 크기/줄: 5,385 bytes / 136 lines
- SHA-256: `5128b8f9dfe282d85b477aed39f2a7d95fe39a1801f4ea20be36ed661e4c0d80`
- 분류/결정: `LEGACY_TEST` / `MAP_AND_REPLACE`
- 의존: `../backend/agy-bridge.mjs`, `node:assert/strict`, `node:crypto`, `node:fs/promises`, `node:os`, `node:path`, `node:test`
- export: 명시 export 추출 없음
- 위험 신호: 정적 패턴 기준 특이 신호 없음
- 처리 근거: Original behavior is audited; plugin-specific cross-platform tests replace CLI/local-cache assumptions.

## 54. `tests/icon-source-policy.test.mjs`

- 크기/줄: 1,787 bytes / 46 lines
- SHA-256: `03af24e97b3f7907eec784b7b6554f3785b85aaac0ce33cd7e2db7d0bea52f6e`
- 분류/결정: `LEGACY_TEST` / `MAP_AND_REPLACE`
- 의존: `../backend/production-validator.mjs`, `node:assert/strict`, `node:test`
- export: 명시 export 추출 없음
- 위험 신호: 정적 패턴 기준 특이 신호 없음
- 처리 근거: Original behavior is audited; plugin-specific cross-platform tests replace CLI/local-cache assumptions.

## 55. `tests/instruction-coverage.test.mjs`

- 크기/줄: 867 bytes / 25 lines
- SHA-256: `8ded4c7ea4b97e795401b65fea1630d0773ac844bcad2963c5677f5fde45530b`
- 분류/결정: `LEGACY_TEST` / `MAP_AND_REPLACE`
- 의존: `../backend/production-validator.mjs`, `node:assert/strict`, `node:test`
- export: 명시 export 추출 없음
- 위험 신호: 정적 패턴 기준 특이 신호 없음
- 처리 근거: Original behavior is audited; plugin-specific cross-platform tests replace CLI/local-cache assumptions.

## 56. `tests/repair-strategy.test.mjs`

- 크기/줄: 4,462 bytes / 83 lines
- SHA-256: `d48446c99b0caf8f4702bb65ec041115660319c2b5153fd6dc23ed8805c70a5e`
- 분류/결정: `LEGACY_TEST` / `MAP_AND_REPLACE`
- 의존: `../backend/auto-repair.mjs`, `node:assert/strict`, `node:test`
- export: 명시 export 추출 없음
- 위험 신호: 정적 패턴 기준 특이 신호 없음
- 처리 근거: Original behavior is audited; plugin-specific cross-platform tests replace CLI/local-cache assumptions.

## 57. `tests/state-recovery-checkpoint.test.mjs`

- 크기/줄: 2,288 bytes / 58 lines
- SHA-256: `8d4938b1a1f2da54626ef3b0eba497ec3e0d5bc6141e780610570513047979c0`
- 분류/결정: `LEGACY_TEST` / `MAP_AND_REPLACE`
- 의존: `../backend/state-recovery.mjs`, `node:assert/strict`, `node:crypto`, `node:fs`, `node:path`, `node:test`
- export: 명시 export 추출 없음
- 위험 신호: 정적 패턴 기준 특이 신호 없음
- 처리 근거: Original behavior is audited; plugin-specific cross-platform tests replace CLI/local-cache assumptions.

## 58. `tests/tasklist-protocol.test.mjs`

- 크기/줄: 10,997 bytes / 278 lines
- SHA-256: `700950a0f3cbb6c018186f7fba1438b0fa926f21cc177a6f9a78bb45df28b5a4`
- 분류/결정: `LEGACY_TEST` / `MAP_AND_REPLACE`
- 의존: `../backend/pipeline.mjs`, `../backend/production-validator.mjs`, `../backend/tasklist-protocol.mjs`, `node:assert/strict`, `node:test`
- export: 명시 export 추출 없음
- 위험 신호: `local-model/cache-coupling`
- 처리 근거: Original behavior is audited; plugin-specific cross-platform tests replace CLI/local-cache assumptions.

## 59. `tests/tasklist-revision.test.mjs`

- 크기/줄: 11,653 bytes / 203 lines
- SHA-256: `f926b58eabd00de7d524758f7cee614ebff4b575be64796671669e2e82107fc8`
- 분류/결정: `LEGACY_TEST` / `MAP_AND_REPLACE`
- 의존: `../backend/pipeline.mjs`, `../backend/tasklist-protocol.mjs`, `node:assert/strict`, `node:crypto`, `node:fs/promises`, `node:os`, `node:path`, `node:test`
- export: 명시 export 추출 없음
- 위험 신호: 정적 패턴 기준 특이 신호 없음
- 처리 근거: Original behavior is audited; plugin-specific cross-platform tests replace CLI/local-cache assumptions.

## 60. `tests/visual-page-structure.test.mjs`

- 크기/줄: 5,308 bytes / 115 lines
- SHA-256: `e880f58eee83e58e2200ec2e3ce22df51bd5fc4df7d22cee5dbf5fe7789dc7fc`
- 분류/결정: `LEGACY_TEST` / `MAP_AND_REPLACE`
- 의존: `../backend/production-validator.mjs`, `node:assert/strict`, `node:fs/promises`, `node:os`, `node:path`, `node:test`
- export: 명시 export 추출 없음
- 위험 신호: 정적 패턴 기준 특이 신호 없음
- 처리 근거: Original behavior is audited; plugin-specific cross-platform tests replace CLI/local-cache assumptions.

## 61. `tests/web-research.test.mjs`

- 크기/줄: 1,674 bytes / 38 lines
- SHA-256: `a3d26eb33dbcec81eebccd3f96440e260540aa59e82b40a0affcf26834622dc5`
- 분류/결정: `LEGACY_TEST` / `MAP_AND_REPLACE`
- 의존: `../backend/web-research.mjs`, `node:assert/strict`, `node:test`
- export: 명시 export 추출 없음
- 위험 신호: 정적 패턴 기준 특이 신호 없음
- 처리 근거: Original behavior is audited; plugin-specific cross-platform tests replace CLI/local-cache assumptions.

## 62. `tests/workload-delegation.test.mjs`

- 크기/줄: 5,426 bytes / 135 lines
- SHA-256: `a85cdf66d377b26ad2692d1360a39800f1d4f325465b17ed844c904d4937b5e1`
- 분류/결정: `LEGACY_TEST` / `MAP_AND_REPLACE`
- 의존: `../backend/production-validator.mjs`, `node:assert/strict`, `node:fs/promises`, `node:os`, `node:path`, `node:test`
- export: 명시 export 추출 없음
- 위험 신호: `local-model/cache-coupling`
- 처리 근거: Original behavior is audited; plugin-specific cross-platform tests replace CLI/local-cache assumptions.

