# KH_Aw 3.2.0 최종 검증 보고서

## 수행 결과

| 검증 | 결과 |
|---|---|
| Python 강제 로직 테스트 | 37/37 PASS |
| Python 모듈 구문 검사 | PASS, 20개 Python 파일 AST 파싱 |
| Node 검증 스크립트 구문 검사 | 4/4 PASS |
| JSON 스키마·manifest 파싱 | PASS, JSON 15개 |
| Skill YAML/frontmatter 파싱 | PASS, YAML 7개 |
| Plugin manifest 검증 | PASS |
| Marketplace manifest 검증 | PASS |
| 배포본 완전성 검사 | PASS—필수 엔진·스킬·스키마·테스트·CI·감사자료 누락 0 |
| Plugin PACKAGE_MANIFEST 해시·크기 | PASS |
| 공개 패키지 보안 스캔 | PASS, 85개 파일·발견 0 |
| CLI 하위 AI intake end-to-end | PASS |
| 동적 최소 수 | 작은 프로젝트 2개 PASS |
| 동적 최대 수 | 초대형 신호 60개 cap PASS |
| 독립 session 중복 차단 | PASS |
| 결과 SHA-256 중복 차단 | PASS |
| 전체 worker ring 교차검토 커버리지 | PASS |
| 불변 dispatch 계약·물리 호출 영수증 | PASS |
| 대장 AI plan/lead-contract 기반 전체 집계 | PASS |
| 8개 전체 단계 2~60 배정 계약 | PASS |
| 물리 근거 기반 대장 AI 증원·안전 최저치 감소 차단 | PASS |
| 정책·run-lock 변조 탐지·수리 | PASS |
| APK 설치 명령 차단 | PASS |

## Node 의존성 다운로드

현재 실행 환경에서 별도 임시 디렉터리에 `npm install --ignore-scripts --no-audit --no-fund`를 실행했지만 300초 제한 안에 완료되지 않아 강제 종료됐습니다. 따라서 Playwright·axe·Lighthouse·pixelmatch·pngjs의 **실제 다운로드/모듈 로드 결과는 로컬 PASS로 기록하지 않습니다.**

GitHub Actions의 `dependency-bootstrap-smoke` 작업이 실제 npm 설치와 모듈 로드를 검증하도록 구성돼 있습니다. 패키지는 보안과 용량을 위해 `node_modules`를 포함하지 않습니다.
