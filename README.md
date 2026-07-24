# KH_Aw Codex Marketplace Plugin 3.2.0

`KH_Aw`는 Codex 웹에서 GitHub 마켓플레이스를 연결하고 플러그인으로 설치해 사용하는 앱·웹 회사 운영 워크플로입니다. 표시 이름은 `KH_Aw`, 내부 플러그인 ID는 `kh-aw`입니다.

원본 `A2A-antigravityCli(1).zip`의 전체 파일 원장과 핵심 로직을 조사한 뒤, 로컬 CLI·브라우저 프로필·캐시에 의존하던 구조를 Codex 웹용 증거 게이트 플러그인으로 재구성했습니다. 특정 디자인·색상·컨셉은 내장하지 않습니다. 실제 프로젝트를 수행할 때마다 AI가 주제에 맞는 웹/GitHub 본문을 직접 추출하고 모든 페이지의 목업부터 실제 구현까지 진행합니다.

## 핵심 강제 구조

완료 여부는 AI 설명이 아니라 코드가 판정합니다.

- `intake → analyze → research → design → implement → review → test → release` 고정 순서
- 분석폴더 제공/미제공 분기 및 제공 원본 읽기 전용 보호·자동복구
- 사용자 원문 줄 단위 `RAW-*`·`REQ-*` 추적
- 전체 파일 목록·크기·SHA-256 원장
- 검색결과 URL이 아닌 실제 웹/GitHub 본문·추출문·HTTP 상태·해시
- 수동 컨셉·수동 색상·고정 디자인 프리셋 금지
- 전체 페이지 각각의 독립 목업 HTML/SVG·PNG와 전체 시각 구조 보드
- 페이지·영역·필드·로직·기능 ID의 목업→구현→테스트 추적
- 사용자 화면의 프로젝트 적합 이미지와 목적성 모션·`reduced-motion`
- 웹 3브라우저·접근성·반응형·콘솔/네트워크·시각회귀·Lighthouse
- Android 빌드·린트·단위테스트·스크린샷 테스트·APK 미설치 에뮬레이터 상태
- iOS 빌드·단위테스트·Simulator 검증
- 실패 시 수리 티켓·근본원인·실제 파일 수정·재검증·비종료 계속

## 단계별 대장 AI와 2~60개 하위 AI

각 단계는 대장 AI 1개와 독립 하위 AI를 사용합니다.

- 최소 2개, 최대 60개
- 60개 고정 호출 금지
- 파일 수·디렉터리 수·요구사항·페이지·필드·로직·기능·위험·연구 요소·필수 도구·릴리스 산출물을 계산해 단계별 수량 결정
- `/agents` 또는 독립 Codex 태스크의 실제 세션 ID 필요
- 각 하위 AI의 고유 작업 ID·role shard·범위·불변 dispatch JSON·물리 호출 영수증·결과 파일·SHA-256 필요
- 결과 해시·세션 ID 재사용 금지
- 모든 하위 AI 결과가 최소 한 번 검토되는 ring 교차검토 필요
- 대장 AI가 plan fingerprint와 lead-contract SHA-256을 기준으로 모든 결과를 통합하고 충돌·중복·누락을 해결한 물리 집계 파일 필요
- 프롬프트에 “하위 AI를 사용했다”고 쓰는 것만으로는 절대 통과 불가

## 슬러시·네이티브 기능

각 단계에서 `/plan`, `/context`, `/agents`, `/artifact`, `/search`, `/diff`, `/review`, `/test`, `/hooks` 중 해당 기능을 우선 사용합니다. 실제 Codex 표면에서 사용할 수 있으면 세션 ID·호출문·결과 파일을 기록합니다. UI 기능을 subprocess로 호출할 수 없는 표면에서는 파일·Git·본문·브라우저·도구 기반 물리 fallback을 실행합니다.

단, `/agents` fallback은 배정표 생성에만 사용되며 **실제 하위 AI 완료로 인정되지 않습니다.** 하위 AI 게이트는 독립 Codex 세션 결과를 별도로 요구합니다.

## APK 설치 제외

APK/AAB 빌드는 허용하지만 설치는 하지 않습니다. 다음 패턴은 실행 전후 이중 차단됩니다.

```text
adb install
pm install
installDebug
connectedAndroidTest
bundletool install-apks
```

## 패키지 구조

```text
.agents/plugins/marketplace.json
plugins/kh-aw/.codex-plugin/plugin.json
plugins/kh-aw/skills/*/SKILL.md
plugins/kh-aw/scripts/kh_aw_cli.py
plugins/kh-aw/scripts/kh_aw/*.py
plugins/kh-aw/scripts/*.mjs
plugins/kh-aw/schemas/*.schema.json
plugins/kh-aw/tests/test_kh_aw.py
audit/*
```

상세 문서:

- `INSTALL_CODEX_WEB.md`
- `FULL_STAGE_REPORT.md`
- `NATIVE_AND_TOOL_ENFORCEMENT_REPORT.md`
- `FINAL_SCORE_REPORT.md`
- `plugins/kh-aw/references/RUNBOOK_KO.md`
