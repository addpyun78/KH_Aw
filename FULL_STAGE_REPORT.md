# KH_Aw 3.2 전체 단계 보고서

## 공통 실행 원칙

모든 단계는 대장 AI가 현재 프로젝트 규모를 계산하고 독립 하위 AI를 최소 2개, 최대 60개 범위에서 배정한다. 대장 AI는 계산된 안전 최저치보다 줄일 수 없으며 실제 프로젝트 근거 파일이 있을 때만 증원할 수 있다. 60개 고정 호출은 금지된다. 각 worker는 고유 세션·작업·role shard·범위·불변 dispatch JSON·호출 영수증·결과 파일·SHA-256을 가져야 한다. 모든 worker는 ring 구조로 다른 worker를 검토하며, 대장 AI가 plan fingerprint와 lead-contract SHA-256에 따라 모든 결과를 집계해야 단계 게이트를 실행할 수 있다.

실패 시 현재 단계를 `repairing`으로 유지하고 배정표 재생성 또는 누락 worker 재호출, 실제 파일 수정, 도구 재실행, 동일 게이트 재검증을 수행한다.

## 1. Intake

목적: 사용자 원문과 실행 경계를 불변 계약으로 고정한다.

강제 산출물:

- `contract/user-instructions.txt`
- `contract/requirements.json`
- `contract/run-lock.json`
- `contract/native-capability-policy.json`
- `contract/tool-policy.json`
- `contract/subagent-orchestration-policy.json`
- intake agent plan·worker별 dispatch contract·invocation receipt·worker ledger·ring review·lead contract·lead aggregation

대표 하위 AI 역할:

- 요구사항 원문 보존
- 제약사항 감사
- 분석폴더 모드 검증
- 경로 안전 검증
- 정책 잠금 교차검토

통과 조건: 원문 줄과 요구사항 ID가 1:1이며 실행 경로·대상 플랫폼·APK 설치 금지·2~60 하위 AI 정책이 잠겨 있어야 한다.

## 2. Analyze

목적: 분석 대상 전체를 파일·구조·페이지·필드·로직·기능 단위로 전수조사한다.

대표 하위 AI 역할:

- 전체 파일 원장
- 아키텍처
- 요구사항 추적
- 페이지 흐름
- 데이터 모델
- 비즈니스 로직
- 보안
- 성능
- 플랫폼
- 접근성
- 교차검토

대규모 프로젝트에서는 파일 수·디렉터리 수·요구사항·위험 수에 따라 worker가 증가한다.

통과 조건: 모든 파일의 물리 목록·SHA-256, 모든 핵심 영역 조사, 누락 0, 분석폴더 원본 무변조가 필요하다.

## 3. Research

목적: 프로젝트마다 실제 웹·GitHub 본문을 추출해 기능·디자인 근거를 만든다.

필수 연구 영역:

- 경쟁·기능
- 디자인 시스템
- 이미지
- 폰트
- 아이콘
- 모션
- 접근성
- 플랫폼
- 전환

검색 결과 URL만 등록하거나 로그인·CAPTCHA·접근 거부 본문을 증거로 쓰면 실패한다. 수동 컨셉·색상 선택과 고정 프리셋은 금지된다.

## 4. Design

목적: 구현 전에 전체 페이지를 목업용 시각 설계로 완성한다.

강제 사항:

- 분석·요구에서 발견한 전체 페이지 수와 설계 페이지 수 일치
- 페이지별 고유 HTML/SVG 목업
- 페이지별 고유 PNG
- 전체 페이지 시각 구조 보드
- 영역·필드·로직·기능 ID
- 이미지·모션·반응형·접근성·전환 전략
- 소기업 사용자 주목 확보 전략

대표 샘플 몇 개로 전체 페이지를 대체하면 실패한다.

## 5. Implement

목적: 승인된 전체 페이지 목업을 실제 코드·로직·이미지·모션으로 구현한다.

강제 사항:

- 각 페이지의 실제 대상 파일
- 파일 SHA-256
- 목업 영역·필드·기능·로직 ID의 구현 추적
- 이미지 파일·권리·출처·사용 위치
- 목적성 모션과 reduced-motion
- 데이터·백엔드·통합 구현

프롬프트나 구현 완료 문장만으로 통과하지 않는다.

## 6. Review

목적: 실제 실행 화면을 목업·요구사항과 비교한다.

검사 항목:

- 전체 페이지 실제 스크린샷
- 구조·필드·기능·로직
- 이미지·모션·상태
- 겹침·깨짐
- 반응형
- 접근성
- 페이지 간 일관성

웹 대상에서는 실제 브라우저 결과를 검토 장부에 연결한다.

## 7. Test

목적: 플랫폼별 실제 도구를 실행해 품질을 검증한다.

웹:

- lint·unit test·build
- Chromium·Firefox·WebKit
- axe
- 다중 viewport
- console/network
- visual regression
- Lighthouse

Android:

- Gradle build
- unit test
- lint
- 설치 없는 screenshot test
- AVD 목록·부팅·health·system screenshot
- Logcat
- APK 설치 제외 확인

iOS:

- xcodebuild 목록·빌드·단위테스트
- Simulator 목록·부팅·UI 검증

조건부:

- TypeScript typecheck
- npm audit
- Firebase Emulator Suite
- Docker Compose 검증
- Flutter analyze/test/build
- AndroidManifest/OpenAPI 검사

모든 도구는 명령·버전·시각·종료코드·로그·산출물·SHA-256을 기록한다.

## 8. Release

목적: 실제 배포 파일과 회사 운영 문서를 검증한다.

강제 사항:

- 버전
- 모든 릴리스 산출물과 SHA-256
- 설치·롤백·개인정보·지원
- 비용 원장
- 보안 스캔
- 열린 수리 티켓 0
- 릴리스 노트
- 모든 단계 agent plan·dispatch contract·invocation receipt·ledger·lead contract·lead aggregation 해시

모든 게이트가 통과한 경우에만 엔진이 `release-receipt.json`을 생성한다.
