# KH_Aw 3.2 최종 요구사항 반영 감사

- 구현 요구사항: **30개**
- 패키지 반영: **30/30**
- 판정 기준: 문서 문구가 아니라 실제 코드·스키마·테스트·파일 존재 여부

| ID | 요구사항 | 판정 | 주요 증거 |
|---|---|---|---|
| U-01 | 표시 이름 KH_Aw / 내부 ID kh-aw | PASS | `plugins/kh-aw/.codex-plugin/plugin.json` |
| U-02 | 누락·요약·축소·생략 방지 | PASS | `plugins/kh-aw/scripts/kh_aw/contracts.py`<br>`plugins/kh-aw/scripts/kh_aw/gates.py`<br>`audit/ORIGINAL_FILE_INVENTORY.jsonl` |
| U-03 | 정밀 전수조사 | PASS | `audit/FULL_INVENTORY_REPORT.md`<br>`audit/CORE_FILE_BY_FILE_REPORT.md` |
| U-04 | 기존 로직 연구·업그레이드 | PASS | `audit/LOGIC_DEEP_RESEARCH_REPORT.md`<br>`audit/UPGRADE_MAPPING.md` |
| U-05 | 항목별 점수 보고서 | PASS | `FINAL_SCORE_REPORT.md` |
| U-06 | 앱·웹 회사 운영 전 단계 | PASS | `plugins/kh-aw/skills/kh-aw-full-cycle/SKILL.md`<br>`plugins/kh-aw/skills/kh-aw-release-company/SKILL.md` |
| U-07 | Git 마켓플레이스 구조 및 Codex 설치 자료 | PASS_PACKAGE | `.agents/plugins/marketplace.json`<br>`INSTALL_CODEX_WEB.md`<br>`GITHUB_PUBLISH.md` |
| U-08 | 수동 컨셉·색상 선택 제거 | PASS | `plugins/kh-aw/scripts/kh_aw/repair.py`<br>`plugins/kh-aw/scripts/kh_aw/gates.py` |
| U-09 | 검색 URL이 아닌 실제 본문 추출 | PASS | `plugins/kh-aw/scripts/kh_aw/evidence.py`<br>`plugins/kh-aw/scripts/kh_aw/gates.py` |
| U-10 | 목업 시각 설계 선행 | PASS | `plugins/kh-aw/scripts/kh_aw/gates.py`<br>`FULL_STAGE_REPORT.md` |
| U-11 | 샘플이 아닌 전체 페이지별 목업 | PASS | `plugins/kh-aw/scripts/kh_aw/gates.py`<br>`plugins/kh-aw/scripts/render_mockups.mjs` |
| U-12 | 목업→실제 디자인·로직·이미지 추적 | PASS | `plugins/kh-aw/scripts/kh_aw/gates.py`<br>`plugins/kh-aw/references/ARTIFACT_CONTRACTS_KO.md` |
| U-13 | 소기업용 고품질·주목·전환 설계 | PASS | `plugins/kh-aw/references/COMPANY_QUALITY_KO.md`<br>`plugins/kh-aw/scripts/kh_aw/gates.py` |
| U-14 | 이미지·목적성 모션·reduced-motion | PASS | `plugins/kh-aw/scripts/kh_aw/gates.py`<br>`plugins/kh-aw/skills/kh-aw-research-design/SKILL.md` |
| U-15 | 실패 시 시스템 정지 금지 | PASS | `plugins/kh-aw/scripts/kh_aw_cli.py`<br>`plugins/kh-aw/scripts/kh_aw/repair.py` |
| U-16 | 전 단계 자동수리·재검증·계속 | PASS | `plugins/kh-aw/scripts/kh_aw/repair.py`<br>`plugins/kh-aw/scripts/kh_aw/gates.py` |
| U-17 | 프롬프트가 아닌 물리 로직 강제 | PASS | `plugins/kh-aw/scripts/kh_aw/gates.py`<br>`plugins/kh-aw/schemas/physical-evidence.schema.json` |
| U-18 | 분석폴더 있음/없음 분기 | PASS | `plugins/kh-aw/scripts/kh_aw/contracts.py`<br>`plugins/kh-aw/scripts/kh_aw_cli.py` |
| U-19 | 분석폴더 읽기 전용 보호·자동복구 | PASS | `plugins/kh-aw/scripts/kh_aw/protection.py` |
| U-20 | Codex 웹 마켓플레이스 플러그인 규격 | PASS | `.agents/plugins/marketplace.json`<br>`plugins/kh-aw/.codex-plugin/plugin.json` |
| U-21 | 특정 디자인 하드코딩 금지·프로젝트별 동적 연구 | PASS | `plugins/kh-aw/scripts/kh_aw/evidence.py`<br>`plugins/kh-aw/scripts/kh_aw/gates.py` |
| U-22 | 단계별 슬러시/네이티브 기능 또는 물리 fallback | PASS | `plugins/kh-aw/scripts/kh_aw/capabilities.py`<br>`plugins/kh-aw/schemas/native-capability-policy.schema.json` |
| U-23 | 브라우저·에뮬레이터·시뮬레이터·전문 QA 도구 | PASS | `plugins/kh-aw/scripts/kh_aw/tooling.py`<br>`plugins/kh-aw/scripts/android_emulator_suite.py`<br>`plugins/kh-aw/scripts/ios_simulator_suite.py`<br>`plugins/kh-aw/scripts/web_verify.mjs` |
| U-24 | APK 설치 제외 | PASS | `plugins/kh-aw/scripts/kh_aw/tooling.py`<br>`plugins/kh-aw/tests/test_kh_aw.py` |
| U-25 | 정책·run-lock·해시 변조 차단 | PASS | `plugins/kh-aw/scripts/kh_aw/run_lock.py`<br>`plugins/kh-aw/scripts/kh_aw/gates.py` |
| U-26 | 8단계별 대장 AI | PASS | `plugins/kh-aw/scripts/kh_aw/orchestration.py`<br>`plugins/kh-aw/schemas/subagent-orchestration.schema.json` |
| U-27 | 각 단계 하위 AI 최소 2·최대 60 | PASS | `plugins/kh-aw/scripts/kh_aw/orchestration.py`<br>`plugins/kh-aw/tests/test_kh_aw.py` |
| U-28 | 프로젝트 규모 기반 동적 수량·근거 기반 증원 | PASS | `plugins/kh-aw/scripts/kh_aw/orchestration.py`<br>`plugins/kh-aw/skills/kh-aw-multi-agent-orchestration/SKILL.md` |
| U-29 | worker별 불변 dispatch·호출 영수증·ring 검토·대장 집계 | PASS | `plugins/kh-aw/scripts/kh_aw/orchestration.py`<br>`plugins/kh-aw/tests/test_kh_aw.py` |
| U-30 | 최종 배포 파일 자체 누락 차단 | PASS | `plugins/kh-aw/scripts/kh_aw/distribution.py`<br>`plugins/kh-aw/scripts/kh_aw_cli.py` |

## 외부에서만 확인 가능한 운영 항목

- GitHub 원격 브랜치가 실제로 게시됐는지
- 사용자 Codex 웹 워크스페이스가 custom Git marketplace 설치를 허용하는지
- 대상 프로젝트 PC/CI에 SDK·브라우저·AVD·Simulator가 설치돼 실제 도구 체인이 통과하는지

위 세 항목은 패키지 내부 구현 누락이 아니라 외부 계정·환경 상태입니다.
